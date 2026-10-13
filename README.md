[download]: https://github.com/diogo-webber/vox-launcher/releases/latest/download/VoxLauncher.zip
[download_count]: https://img.shields.io/github/downloads/diogo-webber/vox-launcher/total?style=for-the-badge&labelColor=%232d333b&color=%23066094
[version]: https://img.shields.io/github/v/release/diogo-webber/vox-launcher?style=for-the-badge&labelColor=%232d333b&color=%23066094
[python_version]: https://img.shields.io/badge/Python-3.14-blue?style=for-the-badge&labelColor=%232d333b&color=%23066094
[video_tutorial]: https://youtu.be/dxl-RV0LtEA
[locales]: https://ss64.com/locale.html
[pull_request]: https://github.com/diogo-webber/vox-launcher/compare/
[new_issue]: https://github.com/diogo-webber/vox-launcher/issues/new
[token_website]: https://accounts.klei.com/account/game/servers?game=DontStarveTogether
[pyinstaller_repo]: https://github.com/pyinstaller/pyinstaller
[windows_defender_tutorial]: https://support.microsoft.com/en-us/windows/add-an-exclusion-to-windows-security-811816c0-4dfd-af4a-47e4-c301afe13b26

<h1 align="center">

  ![GitHub Release][version]
  &ensp;
  ![GitHub Downloads][download_count]
  &ensp;
  ![Python Version][python_version]

</h1>

<br>

<img src="/app/assets/icon.ico" align="left" width="185px"/>

### Vox Launcher

> A dedicated server launcher for Don't Starve Together.

<br><br><br><br><br>

Vox Launcher is a Windows-only app that makes it easy to create and manage Don't Starve Together dedicated servers.

<br>

### Features
- Buttons to **save**, **reset**, **rollback**, and **stop** the server.
- A log screen with a built-in console for running commands.
- Live server info, such as **player count**, **day**, **season**, and **memory usage**.
- Support for mods and any number of shards.

<br>

## Quick Start

<br>

1. [**Download the latest release**][download].
2. Extract the zip and run `Vox Launcher.exe`.
3. Under `Game Directory`, select your game installation folder (if it wasn't detected automatically).
4. Create a world in-game, then select it under `Cluster Directory`.
5. Paste your token under `Server Token`. Hover over the ⓘ icon in the app for instructions on how to get one.
6. Click `LAUNCH` and have fun!

<br>

<dl><dd><dl>

> [!TIP]  
> Additionally, check out this amazing **[video tutorial][video_tutorial]** by Jazzy Games on YouTube for a step-by-step guide.

</dl></dd></dl>

<br>

## Frequently Asked Questions

<br>

- **Why is Windows Defender flagging Vox Launcher as a threat?**

<dl><dd><dl><dd><dl>

> The launcher is packaged using [**PyInstaller**][pyinstaller_repo], a tool often used to bundle Python apps into executables. Unfortunately, malicious software also uses PyInstaller, causing false positives.
>  
> A new release usually resolves the issue temporarily. Long-term, the solution would involve rewriting the app in another language — something I currently don't plan to do.
>  
> You can safely [**add an exclusion in Windows Defender**][windows_defender_tutorial].

</dl></dd></dl></dd></dl>

<br>

- **Are mods supported? How do I enable them?**

<dl><dd><dl><dd><dl>

> Yes! Simply enable them when creating your world in-game. That’s all you need to do.

</dl></dd></dl></dd></dl>

<br>

- **How can I change something about the world? Like the server name or the enabled mods?**

<dl><dd><dl><dd><dl>

> Edit these via the in-game menu, then launch the world once from within the game to apply the changes.
> Launching it through the game is required for the changes to be saved!

</dl></dd></dl></dd></dl>

<br>

- **How do I get a Server Token?**

<dl><dd><dl><dd><dl>

> You can create one on the [**Klei Accounts**][token_website] page.

</dl></dd></dl></dd></dl>

<br>

- **I found a bug. Where should I report it?**

<dl><dd><dl><dd><dl>

> Report issues in the [**Issues Tab**][new_issue].  
> Please include the app log file (`appdata/logs/applog.txt`).

</dl></dd></dl></dd></dl>

<br>

### Troubleshooting

<br>

- **The `Cluster Directory` field says "Invalid Cluster".**

<dl><dd><dl><dd><dl>

> Select a world folder created by the in-game menu (e.g. `Cluster_1`). It must contain a `cluster.ini` file and a `Master` folder, and be inside your Klei account folder, usually `Documents/Klei/DoNotStarveTogether/<numbers>/`.  
> Cloud saves are not supported.

</dl></dd></dl></dd></dl>

<br>

- **The `Server Token` field says "Token Rejected".**

<dl><dd><dl><dd><dl>

> The token may have expired, been revoked, or be in use by another running server. Generate a new one on the [**Klei Accounts**][token_website] page.

</dl></dd></dl></dd></dl>

<br>

- **The launcher asks me to launch a world from the in-game menu first.**

<dl><dd><dl><dd><dl>

> Vox Launcher needs some configuration data that the game generates the first time you host a world. Launch any world from the in-game menu, wait for it to start, stop it, then click `Try Again`.

</dl></dd></dl></dd></dl>

<br>

- **The server fails to start with a port error.**

<dl><dd><dl><dd><dl>

> Another program (including a server hosted in-game) is likely using the same ports. Close any other running servers, or change the ports in each shard's `server.ini` file.

</dl></dd></dl></dd></dl>

<br>

- **The server crashed with a Lua error.**

<dl><dd><dl><dd><dl>

> This is a game crash, not a Vox Launcher issue. Common causes are incompatible or outdated mods, corrupted save data, or a game bug. Try disabling recently added mods, or report it to Klei.

</dl></dd></dl></dd></dl>

<br>

## App Showcase

<br>

<div align="center">

| Instructions | Starting Server |
| :---: | :---: |
| <img src="/.github/readme_assets/offline.png"/> | <img src="/.github/readme_assets/starting.png"/> |
| **Server Online** | **Log Screen** |
| <img src="/.github/readme_assets/online.png"/> | <img src="/.github/readme_assets/logscreen.png"/> |

</div>

<br>

## Contributing

<br>

Contributions are welcome! You can suggest features, report or fix bugs, and submit pull requests.

<br>

#### Running from source

Requires Python 3.14. From the project root:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app/main.py
```

<br>

#### Building from source

The build script requires a virtual environment named `.venv` or `venv` in the project root (see above).

- Run `tools\build_app.bat` to check localizations and build the app with PyInstaller.
- Build output is written to the `builds/` folder.

<br>

#### Translating

1. Create a file in `app/localization/` named `{locale}.yaml`, where `{locale}` is the language code (see **[this list][locales]**).
2. Use `en_US.yaml` as a template. Try to keep translations similar in length to avoid layout issues.
3. Submit a **[Pull Request][pull_request]** titled `Added {Language} ({locale}) localization`.

Available languages:
- English (`en_US`)
- Chinese, Simplified (`zh_CN`)
- Czech (`cs_CZ`)
- Portuguese, Brazilian (`pt_BR`)
- Russian (`ru_RU`)
- Spanish (`es_ES`)
- Thai (`th_TH`)
- Vietnamese (`vi_VN`)

<br><br>

## Contributors

<br>

Big thanks to everyone who contributed to this project:

### Translators

<div align="center">

<a href="https://github.com/ClifffordW"> <img align="left" src="https://avatars.githubusercontent.com/u/55302963?v=4" width=10%/> </a>
<a href="https://github.com/Noctice"> <img align="left" src="https://avatars.githubusercontent.com/u/47233045?v=4" width=10%/> </a>
<a href="https://github.com/bitasuperactive"> <img align="left" src="https://avatars.githubusercontent.com/u/62368693?v=4" width=10%/> </a>
<a href="https://github.com/mihime"> <img align="left" src="https://avatars.githubusercontent.com/u/47947224?v=4" width=10%/> </a>
<a href="https://github.com/hlquang"> <img align="left" src="https://avatars.githubusercontent.com/u/113676018?v=4" width=10%/> </a>


</div>

<br><br><br><br><br>

### Testers

<div align="center">

<a href="https://steamcommunity.com/profiles/76561198797720910"> <img align="left" src="https://avatars.akamai.steamstatic.com/f999d2d7a22aacaef6e6f2f74f2d50053a2e60c4_full.jpg" width=10%/> </a>
<a href="https://steamcommunity.com/profiles/76561198367734754"> <img align="left" src="https://avatars.akamai.steamstatic.com/ea742646678653121528572356e8f287892734c7_full.jpg" width=10%/> </a>

</div>

<br><br><br><br>

<br><br>

## License

<br>

This project is licensed under the MIT License. See the [**LICENSE**](LICENSE) file for details.
