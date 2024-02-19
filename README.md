[download]: https://github.com/diogo-webber/vox-launcher/releases/latest/download/VoxLauncher.zip

<img src="/app/assets/icon.ico" align="left" width="185px"/>

# Vox Launcher

> A Don't Starve Together dedicated server launcher.

<br><br><br><br>

**Vox Launcher** is a dedicated server launcher, created to replace the classic bat files. 

It contains a handful of useful features such as buttons to **save**, **reset**, **rollback** and **stop** the server, a screen that shows the **logs**, a **console**, etc.
It also shows information about the server, such as **number of players**, **day count**, **season** and **memory usage**. It supports any number of shards and it's **Windows only**.

<br>

## How it works?

<br>

- Download the `App` zip, extract its contexts and start the `Vox Launcher` executable. [**Click here**][download] to download it.
- Select the game installation folder under `Game Directory`, if it has not been automatically selected.
- Create a world using the in game menu and select it under `Cluster Directory`.
- Paste a server token under `Server Token`. See instructions on how to obtain one in the app.
- Finnaly, click on the `LAUNCH` button and have fun!

<br><br>

## App Images

<br>

From top left to bottom right: `Instructions`, `Starting Server`, `Server Online`, `Log Screen`.

<br><br>

<img align="left" src="/github_assets/offline.png" width=45%/>
<img align="left" src="/github_assets/starting.png" width=45%/>

<br><br><br><br><br><br><br><br><br><br><br><br>

<img align="left" src="/github_assets/online.png" width=45%/>
<img align="left" src="/github_assets/logscreen.png" width=45%/>

<br><br><br><br><br><br><br><br><br><br><br><br><br><br>

## 📌 Contributing

<br>

Feel free to suggest features and create pull requests to fix bugs. The entry point is `app/main.py`.

<br>

Installing dependencies:
```sh
  python -m pip install -r requirements.txt
```

<br><br>

## 📜 License

<br>

This project is under MIT license. See the [**LICENSE**](LICENSE) file for more details.
