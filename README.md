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
  ![Python Version)][python_version]

</h1>

<br>

<img src="/app/assets/icon.ico" align="left" width="185px"/>

### Vox Launcher

> A Don't Starve Together dedicated server launcher.

<br><br><br><br><br>

A windows only launcher that simplify the creation and usage of dedicated servers.

<br>

### Included features:
- Buttons to **save**, **reset**, **rollback** and **stop** the server.
- A screen that shows server logs and has a console for executing commands.
- Shows information about the server, such as **number of players**, **day count**, **season** and **memory usage**.
- Supports mods and any number of shards.

<br>

## How it works?

<br>

-  Download the `App` zip clicking [**here**][download].
- Extract its contents and start the `Vox Launcher` executable.
- Select the game installation folder under `Game Directory`, if it has not been automatically populated.
- Create a world using the in-game menu and select it under `Cluster Directory`.
- Paste a server token under `Server Token`. See instructions on how to obtain one in the app.
- Finally, click on the `LAUNCH` button and have fun!

<br>

<dl><dd><dl>
  
> [!TIP]
> Additionally, check out this amazing **[video tutorial][video_tutorial]** by Jazzy Games on YouTube.

</dl></dd></dl>

<br>

## Frequently Asked Questions

<br>

- **Windows Defender is flagging Vox Launcher as a threat, why is this happening?**

<dl><dd><dl><dd><dl>
 
> The tool called [**Pyinstaller**][pyinstaller_repo], which is used to bundle the app into an executable, is also used by people who actually make malicious software. Windows Defender recognizes some similar patterns in the executable and includes Vox Launcher as a threat.

> Usually creating a new version solves this temporarily, but there's not much to be done in the long term other than rebuilding the whole app in another programming language, which I don't have the time or desire to do at the moment. The only thing you could do is to [**add an exclusion to Windows Defender**][windows_defender_tutorial].

</dl></dd></dl></dd></dl>

<br>

- **Are mods supported? What do I need to do to enable them?**

<dl><dd><dl><dd><dl>
 
> Yes, they are. Just enable them when you're creating the world, it's that simple!

</dl></dd></dl></dd></dl>

<br>

- **How can I change something about the world? Like the server name or the enabled mods?**

<dl><dd><dl><dd><dl>
 
> Just edit these in the in-game menu and launch the world via the in-game menu once.<br>
> Launching it through the game is essential for saving the changes!

</dl></dd></dl></dd></dl>

<br>

- **How do I get a Cluster Token?**

<dl><dd><dl><dd><dl>
 
> You can create one on the [**Klei Accounts**][token_website] website.

</dl></dd></dl></dd></dl>

<br>

- **I've found a problem in the app, where should I report it?**

<dl><dd><dl><dd><dl>
 
> You may create a issue in the [**Issues Tab**][new_issue].</br>Please attach the app log file when doing so. It can be found at `appdata/logs/applog.txt`.

</dl></dd></dl></dd></dl>

<br>

## App Showcase

<br>

From top left to bottom right: `Instructions`, `Starting Server`, `Server Online`, `Log Screen`.

<br>

<div align="center">

<img align="left" src="/github_assets/offline.png" width=45%/>
<img align="left" src="/github_assets/starting.png" width=45%/>

</div>

<br><br><br><br><br><br><br><br><br><br><br><br><br>

<div align="center">

<img align="left" src="/github_assets/online.png" width=45%/>
<img align="left" src="/github_assets/logscreen.png" width=45%/>

</div>


<br><br><br><br><br><br><br><br><br><br><br><br><br><br>

## 📌 Contributing

<br>

Feel free to suggest features and create pull requests to fix bugs or improve existing code. The entry point is `app/main.py`.

#### You can also help by translating the app:
- Create a file in `app/localization/` called `locale.yaml`, where locate is the language code, which you can find in **[this website][locales]**.
  
- Use `en_US.yaml` as a template. Please, try to keep sentence lengths close to the English version to avoid visual issues.
  
- Create a **[Pull Request][pull_request]** with the title: `Added {language} ({lang_code}) localization`

<br>

#### Installing dependencies:
```ruby
  python -m pip install -r requirements.txt
```

<br><br>

## ❤️ Contributors

<br>

I would like to thank these people for helping with this project:

### Translators

<div align="center">

<a href="https://github.com/ClifffordW"> <img align="left" src="https://avatars.githubusercontent.com/u/55302963?v=4" width=10%/> </a>
<a href="https://github.com/Noctice"> <img align="left" src="https://avatars.githubusercontent.com/u/47233045?v=4" width=10%/> </a>
<a href="https://github.com/VitaBh"> <img align="left" src="https://avatars.githubusercontent.com/u/148809528?v=4" width=10%/> </a>

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
