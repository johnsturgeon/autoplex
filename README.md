# AutoPlex

Utilities and scripts for plex using the Plex API to clean up and manage your Plex Music library.

<img width="300" src="https://github.com/johnsturgeon/plex-tools/assets/9746310/0c42ce63-983b-43a6-8f2e-77338e204cba" alt="GoshDarned Mascot">

---

[Prioritized backlog · Create a website for the plex-tools](https://github.com/users/johnsturgeon/projects/8)

## Deployment instructions

### Linux Installation Notes

* I've installed this on a bare bones Debian 12 LXC (in ProxMox).  The script will work for that environment.  I've not tested for any other distribution, testers are welcome!

### Prerequisites
* [Infisical](https://infisical.com) for secrets management (optional)
* Linux OS (Debian 12 tested)

### Installation script: [deploy.sh](scripts/deploy.sh)

1. Download the installation script 
    ```shell
    wget -q https://github.com/johnsturgeon/autoplex/raw/main/scripts/deploy.sh
    chmod +x deploy.sh
    ```
2. Edit the deployment script and change the following variables to your situation:
    * `INSTALL_DIR`
    * `USE_INFISICAL`

3. Execute the script
    * NOTE: I installed this as `root`, you can `sudo` if necessary
```shell
./deploy.sh
```
