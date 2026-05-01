from catan_app import CatanGame


def max_adjacent_same_resource(game: CatanGame) -> int:
    count = 0
    seen = set()
    for tile in game.tiles:
        tile_vertices = set(tile.vertices)
        for other in game.tiles:
            if tile.hid >= other.hid:
                continue
            if tile.terrain == "desert" or other.terrain == "desert":
                continue
            if tile.terrain != other.terrain:
                continue
            if len(tile_vertices & set(other.vertices)) >= 2:
                seen.add((tile.hid, other.hid))
                count += 1
    return count


def adjacent_hot_numbers(game: CatanGame) -> int:
    count = 0
    for tile in game.tiles:
        tile_vertices = set(tile.vertices)
        for other in game.tiles:
            if tile.hid >= other.hid:
                continue
            if tile.number not in (6, 8) or other.number not in (6, 8):
                continue
            if len(tile_vertices & set(other.vertices)) >= 2:
                count += 1
    return count


def run_game(player_count: int) -> None:
    game = CatanGame(player_count, 0, [])
    while game.phase != "play":
        game.cpu_take_setup()
    for _ in range(player_count * 3):
        game.cpu_take_turn()
        if game.winner is not None:
            break
    assert len(game.tiles) == (19 if player_count == 4 else 30)
    assert len(game.port_markers) == (9 if player_count == 4 else 11)
    assert all(player.roads_left <= 13 for player in game.players)
    assert sum(1 for tile in game.tiles if tile.robber) == 1
    assert max_adjacent_same_resource(game) <= (2 if player_count == 4 else 4)
    assert adjacent_hot_numbers(game) == 0


if __name__ == "__main__":
    run_game(4)
    run_game(6)
    print("smoke test passed")
