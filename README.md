# AutoPlex

<img width="300" src="https://github.com/johnsturgeon/plex-tools/assets/9746310/0c42ce63-983b-43a6-8f2e-77338e204cba" alt="GoshDarned Mascot">

---

> **Work in Progress:** This project is being migrated to a Docker container-based deployment. Documentation and architecture are actively changing.

---

## Development Notes
### 2. Create the CONFIG environment file: 

* _Production_: `config/.env.production`
* _Development_: `config/.env.development`

Make sure to import that environment file prior to running, for examply in PyCharm, I add it to the run configuration under `Paths to .env files`


> See the `config/op.env` for example config
 
<details>

<summary> 💡How to use 1Password to generate .env file </summary>

> If you use 1password for your secrets, you can use the [op.env](config/op.env) file as a template for generating your config file

- [Install op](https://support.1password.com/command-line-getting-started/)
- `export OP_SERVICE_ACCOUNT_TOKEN=<your token>`
- `op vault list` (to test)
- Run the convenience script to create the env file with `op inject`
  - Production [scripts/create_local_prod_env.sh](scripts/create_prod_env.sh) 
  - Development [scripts/create_local_dev_env.sh](scripts/create_local_dev_env.sh)
</details>
