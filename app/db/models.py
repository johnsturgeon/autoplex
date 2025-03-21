from datetime import datetime, UTC
from typing import Dict, List, Optional

from dateutil import parser
from plexapi import exceptions
from plexapi.audio import Track
from plexapi.library import MusicSection
from pydantic import computed_field
from sqlalchemy import delete
from sqlmodel import SQLModel, Field, Relationship, select, Session

from app.plex.api import (
    get_server_list_from_plex,
    get_plex_user_data_from_plex,
    get_track_list_from_plex_library,
    get_library_list_from_plex,
)


class PlexTrack(SQLModel, table=True):
    """Model class for wrapping Plex library track"""

    rating_key: int = Field(primary_key=True)
    guid: str
    flagged_for_deletion: bool
    title: str
    artist: str
    album: str
    duration: int
    audio_codec: str
    bitrate_kbps: int
    added_at: datetime
    play_count: int
    filepath: str
    library_id: str = Field(
        index=True, foreign_key="plexlibrary.uuid", ondelete="CASCADE"
    )
    library: "PlexLibrary" = Relationship(back_populates="tracks")
    hash_value: str

    @staticmethod
    def plex_track_from_track(track: Track, library_id: str) -> "PlexTrack":
        new_track: Dict = {
            "rating_key": int(track.ratingKey),
            "guid": track.guid,
            "flagged_for_deletion": False,
            "title": track.title,
            "artist": track.grandparentTitle,
            "album": track.parentTitle,
            "duration": track.duration,
            "audio_codec": track.media[0].audioCodec,
            "bitrate_kbps": track.media[0].bitrate,
            "added_at": track.addedAt,
            "play_count": int(track.viewCount),
            "library_id": library_id,
        }
        new_track["hash_value"] = str(
            f"{new_track['title']}-{new_track['artist']}-{new_track['album']}-{new_track['duration']}"
        )
        if track.media[0].parts[0].file is None:
            new_track["filepath"]: str = "TIDAL"
        else:
            new_track["filepath"]: str = track.media[0].parts[0].file.strip()
        return PlexTrack(**new_track)


class PlexLibrary(SQLModel, table=True):
    """Class representing a Plex Library"""

    uuid: str = Field(primary_key=True)
    section_id: int
    title: str
    server_id: str = Field(
        index=True, foreign_key="plexserver.uuid", ondelete="CASCADE"
    )
    server: "PlexServer" = Relationship(back_populates="libraries")
    tracks: List[PlexTrack] = Relationship(
        back_populates="library", cascade_delete=True
    )


class PlexServer(SQLModel, table=True):
    """Class representing a Plex Server - no persistence"""

    uuid: str = Field(primary_key=True)
    name: str
    user_id: str = Field(index=True, foreign_key="plexuser.uuid", ondelete="CASCADE")
    user: "PlexUser" = Relationship(back_populates="servers")
    libraries: List[PlexLibrary] = Relationship(
        back_populates="server", cascade_delete=True
    )


class Preference(SQLModel, table=True):
    """Class representing a preference"""

    user_id: str = Field(
        index=True, primary_key=True, foreign_key="plexuser.uuid", ondelete="CASCADE"
    )
    key: str = Field(primary_key=True)
    value: str | None = Field(default=None, nullable=True)

    user: "PlexUser" = Relationship(back_populates="preferences")


# noinspection PyTypeChecker,Pydantic
class PlexUser(SQLModel, table=True):
    """Model representing a Plex user."""

    uuid: str = Field(primary_key=True)
    auth_token: str
    name: str
    servers: List[PlexServer] = Relationship(back_populates="user", cascade_delete=True)
    preferences: List[Preference] = Relationship(
        back_populates="user", cascade_delete=True
    )

    # -- private methods --
    def _set_preference(self, session: Session, key: str, value: str):
        # noinspection Pydantic
        statement = (
            select(Preference)
            .where(Preference.user_id == self.uuid)
            .where(Preference.key == key)
        )
        # noinspection PyTypeChecker
        existing_preference = session.exec(statement).first()
        if existing_preference:
            # Update existing preference
            existing_preference.value = value
        else:
            # Insert new preference
            session.add(Preference(user_id=self.uuid, key=key, value=value))

        session.commit()  # Commit changes

    def _set_server_sync_date(self, session: Session, value: Optional[str] = None):
        self._set_preference(session, "server_sync_date", value)

    def _set_server_sync_status(self, session: Session, value: Optional[str] = None):
        self._set_preference(session, "server_sync_status", value)

    @computed_field
    @property
    def preferred_server(self) -> Optional[PlexServer]:
        for preference in self.preferences:
            if preference.key == "server":
                server_pref = preference
                if server_pref.value is not None:
                    for server in self.servers:
                        if server.uuid == server_pref.value:
                            return server
                    assert False, (
                        "The server preference did not match the list of servers"
                    )
        return None

    @computed_field
    @property
    def preferred_music_library(self) -> Optional[PlexLibrary]:
        for preference in self.preferences:
            if preference.key == "music_library" and preference.value:
                if preference.value is not None:
                    if self.preferred_server:
                        for library in self.preferred_server.libraries:
                            if library.uuid == preference.value:
                                return library
                        assert False, (
                            "The library preference did not match the list of libraries"
                        )
        return None

    @computed_field
    @property
    def server_sync_date(self) -> Optional[datetime]:
        for preference in self.preferences:
            if preference.key == "server_sync_date" and preference.value:
                return parser.parse(preference.value)
        return None

    @computed_field
    @property
    def server_sync_status(self) -> Optional[str]:
        for preference in self.preferences:
            if preference.key == "server_sync_status" and preference.value:
                return preference.value
        return None

    # -- public methods --
    def set_server(self, session: Session, value: Optional[str] = None):
        """
        Clears the 'library' preference and sets the new server preference.
        """
        self.set_music_library(session)
        self._set_preference(session, "server", value)

    def set_music_library(self, session: Session, value: Optional[str] = None):
        self._set_preference(session, "music_library", value)

    def sync_servers_with_db(self, session):
        statement = delete(PlexServer).where(PlexServer.user_id == self.uuid)
        session.exec(statement)
        session.commit()
        self._set_server_sync_status(session, "Sync Started")
        for server in get_server_list_from_plex(self.auth_token):
            plex_server: PlexServer = PlexServer(
                user_id=self.uuid,
                uuid=server.clientIdentifier,
                name=server.name,
            )
            try:
                server.connect()
            except exceptions.NotFound as _:
                print("Could not connect to server", server)
                continue
            self._set_server_sync_status(session, f"Adding Server: {plex_server.name}")
            session.add(plex_server)
            self._sync_libraries_with_db(session, plex_server)
        self._set_server_sync_status(session, "Sync Completed")

    def _sync_libraries_with_db(self, session, server: PlexServer):
        library: MusicSection
        for library in get_library_list_from_plex(self.auth_token, server.uuid):
            if library.type == "artist":
                plex_library: PlexLibrary = PlexLibrary(
                    server_id=server.uuid,
                    section_id=library.key,
                    uuid=library.uuid,
                    title=library.title,
                )
                self._set_server_sync_status(
                    session, f"{server.name} - Adding Library: {plex_library.title}"
                )

                session.add(plex_library)
                total_tracks: int = library.totalViewSize(libtype="track")
                self._sync_tracks_with_db(session, plex_library, total_tracks)
        self._set_server_sync_date(session, str(datetime.now(UTC)))

    def _sync_tracks_with_db(self, session, library: PlexLibrary, total_tracks: int):
        current_track: int = 1
        for track in get_track_list_from_plex_library(
            self.auth_token,
            library.server_id,
            library.section_id,
        ):
            plex_track: PlexTrack = PlexTrack.plex_track_from_track(track, library.uuid)
            self._set_server_sync_status(
                session,
                f"{library.title} - Adding Track ({current_track}/{total_tracks}): {track.title}",
            )
            session.add(plex_track)
            current_track += 1


# noinspection Pydantic, PyTypeChecker
async def upsert_plex_user(session: Session, auth_token: str):
    """Updates the user, or inserts if none exists"""
    plex_user: PlexUser = await get_plex_user_from_auth_token(auth_token)
    user_uuid: str = plex_user.uuid
    # Check if the user already exists
    statement = select(PlexUser).where(PlexUser.uuid == user_uuid)
    existing_user = session.exec(statement).first()
    if existing_user:
        # Update existing user
        existing_user.auth_token = plex_user.auth_token
        existing_user.name = plex_user.name
    else:
        # Insert new user
        session.add(plex_user)
    session.commit()
    return plex_user


async def get_plex_user_from_auth_token(auth_token) -> Optional[PlexUser]:
    """
    Retrieve Plex user information using an authentication token.

    This function sends a GET request to the Plex user API endpoint with the
    provided authentication token. If the response is successful, it returns a
    PlexUser object containing the user's details; otherwise, it returns None.

    Args:
        auth_token (str): The authentication token for the Plex user.

    Returns:
        Optional[PlexUser]: A PlexUser object if successful; otherwise, None.
    """
    response_json = await get_plex_user_data_from_plex(auth_token)
    a_user = PlexUser(
        name=response_json["username"],
        auth_token=auth_token,
        uuid=response_json["uuid"],
    )
    return a_user


def query_user_by_uuid(session: Session, uuid: str) -> Optional[PlexUser]:
    # noinspection Pydantic
    statement = select(PlexUser).where(PlexUser.uuid == uuid)
    # noinspection PyTypeChecker
    return session.exec(statement).first()


def query_user_by_token(session: Session, token: str) -> Optional[PlexUser]:
    # noinspection Pydantic
    statement = select(PlexUser).where(PlexUser.token == token)
    # noinspection PyTypeChecker
    return session.exec(statement).first()
