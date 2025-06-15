[download]: https://github.com/diogo-webber/vox-launcher/releases/latest/download/VoxLauncher.zip
[download_count]: https://img.shields.io/github/downloads/diogo-webber/vox-launcher/total?style=for-the-badge&labelColor=%232d333b&color=%23066094
[version]: https://img.shields.io/github/v/release/diogo-webber/vox-launcher?style=for-the-badge&labelColor=%232d333b&color=%23066094
[python_version]: https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&labelColor=%232d333b&color=%23066094
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

Vox Launcher is a Windows-only app designed to simplify creating and managing Don't Starve Together dedicated servers.

<br>

### Features:
- Buttons to **save**, **reset**, **rollback**, and **stop** the server.
- A screen that shows server logs and has a console for running commands.
- Displays key server info, such as **player count**, **day**, **season**, and **memory usage**.
- Supports mods and any number of shards.

<br>

## Quick Start

<br>

- Download the `App` by clicking [**here**][download].
- Extract the zip contents and run `Vox Launcher.exe`.
- Select your game installation folder under `Game Directory`, if it has not been automatically populated.
- Create a world in-game and select it under `Cluster Directory`.
- Paste your server token under `Server Token`. See instructions on how to obtain one in the app.
- Click on the `LAUNCH` button and have fun!

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
> Launching it through the game is essential for saving the changes!

</dl></dd></dl></dd></dl>

<br>

- **How do I get a Cluster Token?**

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

## App Showcase

<br>

From top left to bottom right: `Instructions`, `Starting Server`, `Server Online`, `Log Screen`.

<br>

<div align="center">

<img align="left" src="/.github/readme_assets/offline.png" width=45%/>
<img align="left" src="/.github/readme_assets/starting.png" width=45%/>

</div>

<br><br><br><br><br><br><br><br><br><br><br><br><br>

<div align="center">

<img align="left" src="/.github/readme_assets/online.png" width=45%/>
<img align="left" src="/.github/readme_assets/logscreen.png" width=45%/>

</div>

<br><br><br><br><br><br><br><br><br><br><br><br><br><br>

## 📌 Contributing

<br>

Contributions are welcome! Feel free to suggest new features, submit pull requests, or fix bugs. The entry point is `app/main.py`.

#### You can also help by translating the app:
- Add a file in `app/localization/` named `{locale}.yaml`, where `{locale}` is the language code (see **[this list][locales]**).
  
- Use `en_US.yaml` as a template. Try to keep translations similar in length to avoid layout issues.
  
- Submit a **[Pull Request][pull_request]** titled: `Added {Language} ({locale}) localization`.

<br>

#### Installing dependencies:
```ruby
python -m pip install -r requirements.txt
```

<br><br>

## ❤️ Contributors

<br>

Big thanks to everyone who contributed to this project:

### Translators

<div align="center">

<a href="https://github.com/ClifffordW"> <img align="left" src="https://avatars.githubusercontent.com/u/55302963?v=4" width=10%/> </a>
<a href="https://github.com/Noctice"> <img align="left" src="https://avatars.githubusercontent.com/u/47233045?v=4" width=10%/> </a>
<a href="https://github.com/bitasuperactive"> <img align="left" src="https://avatars.githubusercontent.com/u/62368693?v=4" width=10%/> </a>
<a href="https://github.com/mihime"> <img align="left" src="https://avatars.githubusercontent.com/u/47947224?v=4" width=10%/> </a>

</div>

<br><br><br><br><br>

### Testers

<div align="center">

<a href="https://steamcommunity.com/profiles/76561198797720910"> <img align="left" src="https://avatars.akamai.steamstatic.com/f999d2d7a22aacaef6e6f2f74f2d50053a2e60c4_full.jpg" width=10%/> </a>
<a href="https://steamcommunity.com/profiles/76561198367734754"> <img align="left" src="https://avatars.akamai.steamstatic.com/ea742646678653121528572356e8f287892734c7_full.jpg" width=10%/> </a>

</div>

<br><br><br><br>

<br><br>

## 📜 License

<br>

This project is under MIT license. See the [**LICENSE**](LICENSE) file for more details.
