# Settlers Online

A local Python board-game app inspired by classic island-settlement rules. The main way to play is the browser-based online version hosted from one computer. A desktop Tkinter version is still included as an option.

## Quick Start

Double-click:

```text
start_online_public.bat
```

Choose an option:

```text
1. Start online public game
2. Start desktop game
3. Start online server only
4. Start Cloudflare tunnel only
```

Option `1` starts the online server and a Cloudflare tunnel in two command windows. Keep both windows open while playing.

## Public Online Game

After choosing option `1`, the Cloudflare window prints a temporary public `https://...trycloudflare.com` link. Send that link to the players.

Players open the link in a browser, enter a name, and click `Join`. Each browser can only claim one team/seat. If the same browser clicks `Join` again, it updates that same seat instead of taking another one.

The first person to join is the host. The host chooses 4 or 6 players, chooses CPU difficulty, and clicks `Start Game`. Empty seats become CPU players.

## Local Network Only

Choose option `3` to start only the online server. It prints local URLs:

```text
http://127.0.0.1:8765
http://YOUR_LOCAL_IP:8765
```

Use the local IP URL for players on the same network.

## Spectator Mode

Use `Spectate` to watch without claiming a team. This is useful for a TV or shared display.

Spectators can see the public board, scores, log, current turn, and winner popup. They do not see private resources or development cards.

## Desktop Game

Choose option `2` in `start_online_public.bat` to run the desktop Tkinter version:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" catan_app.py
```

No extra packages are required.

## Gameplay Features

- 4-player base board and 6-player extended board
- Browser-based multiplayer from one host computer
- Optional public link through bundled Cloudflare tunnel
- Spectator mode for TV/shared displays
- CPU players for empty seats
- CPU difficulty: easy, normal, hard
- Randomized terrain, numbers, ports, and robber
- Resource names: Brick, Wood, Sheep, Wheat, Ore
- Setup phase with snake-order settlement and road placement
- Dice production, robber on 7, discard over 7 cards, and stealing
- Robber movement only after rolling a 7 or playing a Knight
- Robber steal target chosen from a dropdown when multiple players can be stolen from
- Roads, settlements, cities, bank/harbor trades, and development cards
- Player trades with human accept/decline and CPU decisions
- Trade popup when another player proposes a trade to you
- Trade privacy: invalid human trade requests auto-decline after a short delay instead of revealing card counts
- Player trades require at least one resource from each side
- Build-cost reference card in the online UI
- Development-card dropdown showing playable and currently unplayable cards
- Monopoly and Year of Plenty use dropdown resource selection
- Road Building lets human players place two free roads manually
- Settlement/city hover highlights touching hexes and port details
- Public scores hide other players' unrevealed Victory Point development cards
- Longest Road, Largest Army, hidden Victory Point cards, and 10 VP win condition
- Winner popup when the game ends
- Player names use board-color swatches in the online UI

## Online Controls

1. Open the game link in a browser.
2. Click `Join` to play, or `Spectate` to watch.
3. The host starts the game after choosing board size and CPU difficulty.
4. During setup, click an intersection for your settlement, then click an adjacent edge for your road.
5. During normal play, click `Roll`, choose an action, then click the board.
6. Use `Player Trade` to offer resources to another player.
7. Use `Bank / Harbor` for bank and port trades.
8. Use `Development Cards` to buy or play development cards.
9. Use the build-cost card to check purchase costs.
10. Click `End Turn` when finished.

## Files

- `start_online_public.bat`: the only launcher batch file
- `online_catan.py`: browser multiplayer server and UI
- `catan_app.py`: shared game logic and desktop Tkinter app
- `Cloudflare\cloudflared-windows-amd64.exe`: bundled tunnel executable

This project uses original UI and visual styling. It does not include official board-game artwork, names, logos, or rulebook text.
