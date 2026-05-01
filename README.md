# Settlers Offline

A fully offline local desktop board-game app inspired by the classic island-settlement ruleset.

## Run

Double-click `run_catan.bat`, or run:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" catan_app.py
```

The app uses Python's built-in Tkinter UI, so no packages need to be installed.

## Online Multiplayer

Double-click `run_online_catan.bat`, or run:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" online_catan.py
```

The server prints two URLs:

- `http://127.0.0.1:8765` for the host computer
- `http://YOUR_LOCAL_IP:8765` for other people on the same network

Everyone opens the same URL in a browser, enters a name, and clicks `Join`. The browser version uses one master board on the host server. Each player sees the shared board, public scores, turn log, and only their own resources/development cards.

For people outside your home network, you will need to host this on a reachable computer or configure router/firewall access to port `8765`.

## What Is Included

- 4-player base-board mode
- 6-player extended-board mode
- Human hot-seat players
- Browser-based online play from one host server
- CPU players to fill the board
- Randomized terrain, number tokens, ports, and robber
- Resource labels use Brick, Wood, Sheep, Wheat, and Ore
- Terrain generation tries to spread resource types out instead of allowing heavy clumps
- Number-token generation spreads high-probability numbers out and prevents adjacent 6/8 tiles
- Number tokens show probability dots like the physical board game
- Setup phase with snake-order initial settlement and road placement
- Dice production, robber on 7, discard over 7 cards, and stealing
- Roads, settlements, cities, bank/harbor trades, and development cards
- Player-to-player trade offers with human accept/decline and simple CPU acceptance
- Build-cost reference card popup
- Development card dropdown showing playable and currently unplayable cards
- Monopoly and Year of Plenty use dropdown resource selection
- Road Building lets human players place two free roads manually
- Settlement/city hover highlights that show the exact spot and port
- Public scoreboard hides other players' unrevealed Victory Point development cards
- CPU trade acceptance considers resource needs, scarcity, harbor rates, and score position
- Longest Road, Largest Army, hidden Victory Point cards, and 10 VP win condition

## Controls

1. Choose 4-player or 6-player mode.
2. Choose how many humans are playing. Empty seats become CPUs.
3. During setup, click an intersection for your settlement, then click an adjacent edge for your road.
4. During normal play, roll first, then choose an action in the right panel and click the board.
5. Read turn history in the log panel on the left.
6. Use `Build Cost Card` to view purchase costs and your current bank/harbor rates.
7. Use `Trade With Player` after rolling to offer resources to another player.
8. Use `Play Development Card` to view all development cards and play eligible ones.
9. After playing Road Building, click two legal road edges to place the free roads.
10. Hover over a settlement or city to highlight the touching hexes and show the spot details.
11. Use `End Turn` when you are finished.

This project uses original UI and visual styling. It does not include official board-game artwork, names, logos, or rulebook text.
