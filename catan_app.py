from __future__ import annotations

import math
import random
import tkinter as tk
from collections import Counter
from dataclasses import dataclass, field
from tkinter import messagebox, ttk


RESOURCES = ["brick", "lumber", "wool", "grain", "ore"]
RESOURCE_LABELS = {
    "brick": "Brick",
    "lumber": "Wood",
    "wool": "Sheep",
    "grain": "Wheat",
    "ore": "Ore",
}
LABEL_TO_RESOURCE = {label: resource for resource, label in RESOURCE_LABELS.items()}
TERRAIN_LABELS = {
    "hills": "Brick",
    "forest": "Wood",
    "pasture": "Sheep",
    "fields": "Wheat",
    "mountains": "Ore",
    "desert": "Desert",
}
TERRAIN_RESOURCE = {
    "hills": "brick",
    "forest": "lumber",
    "pasture": "wool",
    "fields": "grain",
    "mountains": "ore",
    "desert": None,
}
NUMBER_DOTS = {
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    6: 5,
    8: 5,
    9: 4,
    10: 3,
    11: 2,
    12: 1,
}
TERRAIN_COLORS = {
    "hills": "#b7683f",
    "forest": "#2f7d4a",
    "pasture": "#80b855",
    "fields": "#d7bd48",
    "mountains": "#8a8d91",
    "desert": "#d7b977",
    "sea": "#5aa9c9",
}
PLAYER_COLORS = ["#d63a2f", "#f5f2e7", "#2874d0", "#ef8f28", "#2f9e59", "#8a5a35"]
BUILD_COSTS = {
    "road": {"brick": 1, "lumber": 1},
    "settlement": {"brick": 1, "lumber": 1, "wool": 1, "grain": 1},
    "city": {"grain": 2, "ore": 3},
    "development": {"wool": 1, "grain": 1, "ore": 1},
}
PORT_TYPES = ["3:1", "3:1", "3:1", "3:1", "brick", "lumber", "wool", "grain", "ore"]


@dataclass
class HexTile:
    hid: int
    q: float
    r: int
    terrain: str
    number: int | None
    vertices: list[int] = field(default_factory=list)
    robber: bool = False


@dataclass
class Building:
    owner: int
    kind: str


@dataclass
class Player:
    name: str
    color: str
    is_cpu: bool
    resources: dict[str, int] = field(default_factory=lambda: {r: 0 for r in RESOURCES})
    dev_cards: list[str] = field(default_factory=list)
    new_dev_cards: list[str] = field(default_factory=list)
    played_knights: int = 0
    roads_left: int = 15
    settlements_left: int = 5
    cities_left: int = 4

    def resource_count(self) -> int:
        return sum(self.resources.values())


class CatanGame:
    def __init__(self, player_count: int, human_count: int, names: list[str]):
        self.player_count = player_count
        self.human_count = human_count
        self.players = [
            Player(
                names[i] if i < human_count and names[i].strip() else f"Player {i + 1}",
                PLAYER_COLORS[i],
                i >= human_count,
            )
            for i in range(player_count)
        ]
        self.tiles: list[HexTile] = []
        self.vertices: dict[int, tuple[float, float]] = {}
        self.vertex_tiles: dict[int, list[int]] = {}
        self.vertex_neighbors: dict[int, set[int]] = {}
        self.edges: dict[tuple[int, int], int | None] = {}
        self.buildings: dict[int, Building] = {}
        self.ports: dict[int, str] = {}
        self.port_markers: list[tuple[int, int | None, str]] = []
        self.dev_deck: list[str] = []
        self.longest_road_owner: int | None = None
        self.largest_army_owner: int | None = None
        self.current = 0
        self.phase = "setup_settlement"
        self.setup_order = list(range(player_count)) + list(reversed(range(player_count)))
        self.setup_index = 0
        self.pending_setup_vertex: int | None = None
        self.turn_has_rolled = False
        self.dev_played_this_turn = False
        self.awaiting = None
        self.free_roads_remaining = 0
        self.log: list[str] = []
        self.last_roll: int | None = None
        self.winner: int | None = None
        self._build_board()
        self._build_dev_deck()

    def _build_board(self) -> None:
        if self.player_count == 4:
            coords = self._radius_coords(2)
            terrains = ["hills"] * 3 + ["forest"] * 4 + ["pasture"] * 4 + ["fields"] * 4 + ["mountains"] * 3 + ["desert"]
            numbers = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
        else:
            coords = self._extended_coords()
            terrains = ["hills"] * 5 + ["forest"] * 6 + ["pasture"] * 6 + ["fields"] * 6 + ["mountains"] * 5 + ["desert"] * 2
            numbers = [2, 3, 3, 4, 4, 5, 5, 5, 6, 6, 6, 8, 8, 8, 9, 9, 9, 10, 10, 11, 11, 12, 2, 3, 4, 5, 9, 10]
        terrains = self._spread_terrains(coords, terrains)
        numbers = self._spread_numbers(coords, terrains, numbers)
        vertex_by_point: dict[tuple[int, int], int] = {}
        edges_set: set[tuple[int, int]] = set()
        number_index = 0
        for hid, (q, r) in enumerate(coords):
            terrain = terrains[hid]
            number = None
            if TERRAIN_RESOURCE[terrain]:
                number = numbers[number_index]
                number_index += 1
            tile = HexTile(hid, q, r, terrain, number)
            for point in self._hex_points(q, r):
                key = (round(point[0] * 1000), round(point[1] * 1000))
                if key not in vertex_by_point:
                    vid = len(vertex_by_point)
                    vertex_by_point[key] = vid
                    self.vertices[vid] = point
                    self.vertex_tiles[vid] = []
                    self.vertex_neighbors[vid] = set()
                vid = vertex_by_point[key]
                tile.vertices.append(vid)
                self.vertex_tiles[vid].append(hid)
            for i in range(6):
                a = tile.vertices[i]
                b = tile.vertices[(i + 1) % 6]
                edge = tuple(sorted((a, b)))
                edges_set.add(edge)
                self.vertex_neighbors[a].add(b)
                self.vertex_neighbors[b].add(a)
            self.tiles.append(tile)
        self.edges = {edge: None for edge in edges_set}
        desert = next(t for t in self.tiles if t.terrain == "desert")
        desert.robber = True
        self._assign_ports()

    def _radius_coords(self, radius: int) -> list[tuple[float, int]]:
        coords = []
        for q in range(-radius, radius + 1):
            for r in range(-radius, radius + 1):
                if -radius <= -q - r <= radius:
                    coords.append((q, r))
        return sorted(coords, key=lambda c: (c[1], c[0]))

    def _extended_coords(self) -> list[tuple[float, int]]:
        rows = [3, 4, 5, 6, 5, 4, 3]
        coords = []
        for row, length in enumerate(rows):
            r = row - 3
            for i in range(length):
                centered_x = i - (length - 1) / 2
                q = centered_x - r / 2
                coords.append((q, r))
        return coords

    def _spread_terrains(self, coords: list[tuple[float, int]], terrains: list[str]) -> list[str]:
        best = terrains[:]
        best_score = float("inf")
        attempts = 900 if len(terrains) <= 19 else 1400
        for _ in range(attempts):
            candidate = terrains[:]
            random.shuffle(candidate)
            score = self._terrain_clump_score(coords, candidate)
            if score < best_score:
                best = candidate
                best_score = score
                if score == 0:
                    break
        return best

    def _terrain_clump_score(self, coords: list[tuple[float, int]], terrains: list[str]) -> int:
        by_coord = dict(zip(coords, terrains))
        adjacent_pairs = self._coord_adjacencies(coords)
        score = 0
        same_counts = {coord: 0 for coord in coords}
        for a, b in adjacent_pairs:
            terrain = by_coord[a]
            neighbor = by_coord[b]
            if terrain == "desert" or neighbor == "desert":
                continue
            if terrain == neighbor:
                same_counts[a] += 1
                same_counts[b] += 1
                score += 25
            else:
                score -= 1
        score += sum(50 for count in same_counts.values() if count >= 2)
        return score

    def _spread_numbers(self, coords: list[tuple[float, int]], terrains: list[str], numbers: list[int]) -> list[int]:
        playable_coords = [coord for coord, terrain in zip(coords, terrains) if TERRAIN_RESOURCE[terrain]]
        best = numbers[:]
        best_score = float("inf")
        attempts = 1200 if len(numbers) <= 18 else 1800
        for _ in range(attempts):
            candidate = numbers[:]
            random.shuffle(candidate)
            score = self._number_clump_score(playable_coords, candidate)
            if score < best_score:
                best = candidate
                best_score = score
                if score <= 0:
                    break
        return best

    def _number_clump_score(self, playable_coords: list[tuple[float, int]], numbers: list[int]) -> int:
        by_coord = dict(zip(playable_coords, numbers))
        adjacent_pairs = self._coord_adjacencies(playable_coords)
        score = 0
        hot_counts = {coord: 0 for coord in playable_coords}
        for a, b in adjacent_pairs:
            na = by_coord[a]
            nb = by_coord[b]
            dots_a = NUMBER_DOTS[na]
            dots_b = NUMBER_DOTS[nb]
            if na in (6, 8) and nb in (6, 8):
                score += 160
                hot_counts[a] += 1
                hot_counts[b] += 1
            elif dots_a >= 4 and dots_b >= 4:
                score += 45
            elif dots_a + dots_b >= 7:
                score += 12
            if na == nb:
                score += 30
            if abs(na - nb) == 1 and min(dots_a, dots_b) >= 3:
                score += 8
        score += sum(60 for count in hot_counts.values() if count >= 2)
        return score

    def _coord_adjacencies(self, coords: list[tuple[float, int]]) -> list[tuple[tuple[float, int], tuple[float, int]]]:
        centers = {coord: self._coord_center(coord[0], coord[1]) for coord in coords}
        pairs = []
        expected = 46 * math.sqrt(3)
        for i, a in enumerate(coords):
            ax, ay = centers[a]
            for b in coords[i + 1:]:
                bx, by = centers[b]
                if abs(math.hypot(ax - bx, ay - by) - expected) < 0.01:
                    pairs.append((a, b))
        return pairs

    def _coord_center(self, q: float, r: int, size: float = 46) -> tuple[float, float]:
        return size * math.sqrt(3) * (q + r / 2), size * 1.5 * r

    def _hex_points(self, q: float, r: int, size: float = 46) -> list[tuple[float, float]]:
        cx, cy = self._coord_center(q, r, size)
        return [
            (cx + size * math.cos(math.radians(60 * i - 30)), cy + size * math.sin(math.radians(60 * i - 30)))
            for i in range(6)
        ]

    def _assign_ports(self) -> None:
        coast = [v for v, tiles in self.vertex_tiles.items() if len(tiles) <= 2]
        coast.sort(key=lambda v: math.atan2(self.vertices[v][1], self.vertices[v][0]))
        ports = PORT_TYPES + (["3:1", "3:1"] if self.player_count == 6 else [])
        random.shuffle(ports)
        if not coast:
            return
        step = max(1, len(coast) // len(ports))
        used = set()
        self.port_markers = []
        for i, port in enumerate(ports):
            v = coast[(i * step) % len(coast)]
            while v in used:
                v = coast[(coast.index(v) + 1) % len(coast)]
            partner = self._coastal_port_partner(v, used)
            self.ports[v] = port
            used.add(v)
            if partner is not None:
                self.ports[partner] = port
                used.add(partner)
            self.port_markers.append((v, partner, port))

    def _coastal_port_partner(self, vertex: int, used: set[int]) -> int | None:
        candidates = [
            n
            for n in self.vertex_neighbors[vertex]
            if n not in used and len(self.vertex_tiles[n]) <= 2
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda n: (self.vertices[n][0] - self.vertices[vertex][0]) ** 2 + (self.vertices[n][1] - self.vertices[vertex][1]) ** 2)

    def _build_dev_deck(self) -> None:
        self.dev_deck = ["Knight"] * 14 + ["Victory Point"] * 5 + ["Road Building"] * 2 + ["Year of Plenty"] * 2 + ["Monopoly"] * 2
        if self.player_count == 6:
            self.dev_deck += ["Knight"] * 6 + ["Victory Point"] * 2 + ["Road Building", "Year of Plenty", "Monopoly"]
        random.shuffle(self.dev_deck)

    def active_player(self) -> Player:
        return self.players[self.current]

    def add_log(self, text: str) -> None:
        self.log.append(text)
        self.log = self.log[-80:]

    def can_afford(self, p: Player, cost: dict[str, int]) -> bool:
        return all(p.resources[r] >= n for r, n in cost.items())

    def pay(self, p: Player, cost: dict[str, int]) -> None:
        for r, n in cost.items():
            p.resources[r] -= n

    def give(self, p: Player, resources: dict[str, int]) -> None:
        for r, n in resources.items():
            p.resources[r] += n

    def valid_settlement_vertices(self, player_index: int, setup: bool = False) -> list[int]:
        if self.players[player_index].settlements_left <= 0:
            return []
        valid = []
        for v in self.vertices:
            if v in self.buildings:
                continue
            if any(n in self.buildings for n in self.vertex_neighbors[v]):
                continue
            if setup or self._player_road_touches(player_index, v):
                valid.append(v)
        return valid

    def settlement_block_reason(self, player_index: int, vertex: int | None, setup: bool = False) -> str:
        if vertex is None:
            return "Click directly on an open corner intersection."
        if vertex in self.buildings:
            owner = self.players[self.buildings[vertex].owner].name
            return f"That corner already has {owner}'s {self.buildings[vertex].kind}."
        adjacent = [n for n in self.vertex_neighbors[vertex] if n in self.buildings]
        if adjacent:
            names = sorted({self.players[self.buildings[n].owner].name for n in adjacent})
            return "Settlements must be at least two road edges apart. This corner is adjacent to " + ", ".join(names) + "."
        if not setup and not self._player_road_touches(player_index, vertex):
            return "That corner is not connected to one of your roads."
        p = self.players[player_index]
        if p.settlements_left <= 0:
            return "You do not have any settlements left."
        if not setup and not self.can_afford(p, BUILD_COSTS["settlement"]):
            return "You need 1 Brick, 1 Wood, 1 Sheep, and 1 Wheat."
        return "That settlement spot is legal."

    def valid_city_vertices(self, player_index: int) -> list[int]:
        return [v for v, b in self.buildings.items() if b.owner == player_index and b.kind == "settlement"]

    def valid_road_edges(self, player_index: int, setup_vertex: int | None = None) -> list[tuple[int, int]]:
        valid = []
        for edge, owner in self.edges.items():
            if owner is not None:
                continue
            a, b = edge
            if setup_vertex is not None:
                if a == setup_vertex or b == setup_vertex:
                    valid.append(edge)
                continue
            if self._can_extend_from(player_index, a) or self._can_extend_from(player_index, b):
                valid.append(edge)
        return valid

    def _player_road_touches(self, player_index: int, vertex: int) -> bool:
        return any(owner == player_index and vertex in edge for edge, owner in self.edges.items())

    def _can_extend_from(self, player_index: int, vertex: int) -> bool:
        building = self.buildings.get(vertex)
        if building and building.owner != player_index:
            return False
        return self._player_road_touches(player_index, vertex) or (building and building.owner == player_index)

    def place_settlement(self, player_index: int, vertex: int, setup: bool = False) -> bool:
        if vertex not in self.valid_settlement_vertices(player_index, setup):
            return False
        p = self.players[player_index]
        if p.settlements_left <= 0:
            return False
        if not setup:
            if not self.can_afford(p, BUILD_COSTS["settlement"]):
                return False
            self.pay(p, BUILD_COSTS["settlement"])
        self.buildings[vertex] = Building(player_index, "settlement")
        p.settlements_left -= 1
        if setup and self.setup_index >= self.player_count:
            self._grant_starting_resources(p, vertex)
        self.add_log(f"{p.name} built a settlement.")
        self._check_win(player_index)
        return True

    def place_city(self, player_index: int, vertex: int) -> bool:
        p = self.players[player_index]
        if vertex not in self.valid_city_vertices(player_index):
            return False
        if p.cities_left <= 0 or not self.can_afford(p, BUILD_COSTS["city"]):
            return False
        self.pay(p, BUILD_COSTS["city"])
        self.buildings[vertex] = Building(player_index, "city")
        p.cities_left -= 1
        p.settlements_left += 1
        self.add_log(f"{p.name} upgraded to a city.")
        self._check_win(player_index)
        return True

    def place_road(self, player_index: int, edge: tuple[int, int], setup_vertex: int | None = None, free: bool = False) -> bool:
        edge = tuple(sorted(edge))
        if edge not in self.valid_road_edges(player_index, setup_vertex):
            return False
        p = self.players[player_index]
        if p.roads_left <= 0:
            return False
        if not free and setup_vertex is None:
            if not self.can_afford(p, BUILD_COSTS["road"]):
                return False
            self.pay(p, BUILD_COSTS["road"])
        self.edges[edge] = player_index
        p.roads_left -= 1
        self.add_log(f"{p.name} built a road.")
        self._update_longest_road()
        return True

    def _grant_starting_resources(self, p: Player, vertex: int) -> None:
        for hid in self.vertex_tiles[vertex]:
            resource = TERRAIN_RESOURCE[self.tiles[hid].terrain]
            if resource:
                p.resources[resource] += 1

    def roll(self) -> int:
        total = random.randint(1, 6) + random.randint(1, 6)
        self.last_roll = total
        self.turn_has_rolled = True
        self.add_log(f"{self.active_player().name} rolled {total}.")
        if total == 7:
            self._discard_for_seven()
            self.awaiting = "robber"
            self.add_log("Move the robber to a new hex.")
        else:
            self._produce(total)
        return total

    def _produce(self, number: int) -> None:
        produced: dict[int, dict[str, int]] = {}
        for tile in self.tiles:
            if tile.number != number or tile.robber:
                continue
            resource = TERRAIN_RESOURCE[tile.terrain]
            if not resource:
                continue
            for v in tile.vertices:
                building = self.buildings.get(v)
                if building:
                    amount = 2 if building.kind == "city" else 1
                    self.players[building.owner].resources[resource] += amount
                    produced.setdefault(building.owner, {}).setdefault(resource, 0)
                    produced[building.owner][resource] += amount
        if produced:
            parts = []
            for owner, resources in produced.items():
                gains = ", ".join(f"{amount} {RESOURCE_LABELS[resource]}" for resource, amount in resources.items())
                parts.append(f"{self.players[owner].name}: {gains}")
            self.add_log("Produced " + "; ".join(parts) + ".")
        else:
            self.add_log("No resources produced.")

    def _discard_for_seven(self) -> None:
        for p in self.players:
            if p.resource_count() <= 7:
                continue
            discards = p.resource_count() // 2
            for _ in range(discards):
                choices = [r for r, n in p.resources.items() if n > 0]
                if not choices:
                    break
                p.resources[random.choice(choices)] -= 1
            self.add_log(f"{p.name} discarded {discards} cards.")

    def move_robber(self, hid: int) -> None:
        for t in self.tiles:
            t.robber = False
        self.tiles[hid].robber = True
        victims = sorted({self.buildings[v].owner for v in self.tiles[hid].vertices if v in self.buildings and self.buildings[v].owner != self.current})
        victims = [i for i in victims if self.players[i].resource_count() > 0]
        if victims:
            victim = random.choice(victims)
            choices = [r for r, n in self.players[victim].resources.items() if n > 0]
            resource = random.choice(choices)
            self.players[victim].resources[resource] -= 1
            self.players[self.current].resources[resource] += 1
            self.add_log(f"{self.active_player().name} stole from {self.players[victim].name}.")
        self.awaiting = None

    def buy_dev(self, player_index: int) -> bool:
        p = self.players[player_index]
        if not self.dev_deck or not self.can_afford(p, BUILD_COSTS["development"]):
            return False
        self.pay(p, BUILD_COSTS["development"])
        card = self.dev_deck.pop()
        p.dev_cards.append(card)
        p.new_dev_cards.append(card)
        self.add_log(f"{p.name} bought a development card.")
        self._check_win(player_index)
        return True

    def playable_dev_cards(self, player_index: int) -> list[str]:
        p = self.players[player_index]
        new_counts = Counter(p.new_dev_cards)
        playable = []
        for card in p.dev_cards:
            if card == "Victory Point":
                continue
            if new_counts[card] > 0:
                new_counts[card] -= 1
                continue
            playable.append(card)
        return playable

    def play_dev(self, card: str, choice: str | None = None) -> bool:
        p = self.active_player()
        if self.dev_played_this_turn or card not in self.playable_dev_cards(self.current):
            return False
        p.dev_cards.remove(card)
        self.dev_played_this_turn = True
        if card == "Knight":
            p.played_knights += 1
            self.awaiting = "robber"
            self.add_log(f"{p.name} played a knight.")
            self._update_largest_army()
        elif card == "Road Building":
            if p.is_cpu:
                for _ in range(2):
                    edges = self.valid_road_edges(self.current)
                    if edges:
                        self.place_road(self.current, self._cpu_pick_edge(edges), free=True)
                self.add_log(f"{p.name} played Road Building.")
            else:
                self.free_roads_remaining = min(2, p.roads_left, len(self.valid_road_edges(self.current)))
                if self.free_roads_remaining:
                    self.awaiting = "free_road"
                    self.add_log(f"{p.name} played Road Building. Place {self.free_roads_remaining} free roads.")
                else:
                    self.add_log(f"{p.name} played Road Building, but has no legal road placements.")
        elif card == "Year of Plenty":
            choices = [r for r in (choice or "").split(",") if r in RESOURCES]
            if not choices:
                choices = [random.choice(RESOURCES), random.choice(RESOURCES)]
            for resource in choices[:2]:
                p.resources[resource] += 1
            gained = Counter(choices[:2])
            self.add_log(f"{p.name} took {self._resource_bundle_text(dict(gained))}.")
        elif card == "Monopoly":
            resource = choice if choice in RESOURCES else random.choice(RESOURCES)
            total = 0
            for other in self.players:
                if other is p:
                    continue
                total += other.resources[resource]
                other.resources[resource] = 0
            p.resources[resource] += total
            self.add_log(f"{p.name} monopolized {RESOURCE_LABELS[resource]}.")
        self._check_win(self.current)
        return True

    def bank_trade(self, give: str, get: str) -> bool:
        p = self.active_player()
        rate = self.trade_rate(self.current, give)
        if p.resources[give] < rate:
            return False
        p.resources[give] -= rate
        p.resources[get] += 1
        self.add_log(f"{p.name} traded {rate} {RESOURCE_LABELS[give]} for 1 {RESOURCE_LABELS[get]}.")
        return True

    def player_trade(self, from_index: int, to_index: int, offer: dict[str, int], request: dict[str, int]) -> bool:
        if from_index == to_index:
            return False
        giver = self.players[from_index]
        receiver = self.players[to_index]
        if not self._has_resources(giver, offer) or not self._has_resources(receiver, request):
            return False
        for resource, amount in offer.items():
            giver.resources[resource] -= amount
            receiver.resources[resource] += amount
        for resource, amount in request.items():
            receiver.resources[resource] -= amount
            giver.resources[resource] += amount
        offer_text = self._resource_bundle_text(offer)
        request_text = self._resource_bundle_text(request)
        self.add_log(f"{giver.name} traded {offer_text} to {receiver.name} for {request_text}.")
        return True

    def _has_resources(self, player: Player, resources: dict[str, int]) -> bool:
        return all(player.resources[resource] >= amount for resource, amount in resources.items())

    def _resource_bundle_text(self, resources: dict[str, int]) -> str:
        parts = [f"{amount} {RESOURCE_LABELS[resource]}" for resource, amount in resources.items() if amount > 0]
        return ", ".join(parts) if parts else "nothing"

    def trade_rate(self, player_index: int, resource: str) -> int:
        rates = [4]
        for v, building in self.buildings.items():
            if building.owner != player_index or v not in self.ports:
                continue
            port = self.ports[v]
            if port == "3:1":
                rates.append(3)
            elif port == resource:
                rates.append(2)
        return min(rates)

    def score(self, player_index: int) -> int:
        total = 0
        for b in self.buildings.values():
            if b.owner == player_index:
                total += 2 if b.kind == "city" else 1
        total += sum(1 for c in self.players[player_index].dev_cards if c == "Victory Point")
        if self.longest_road_owner == player_index:
            total += 2
        if self.largest_army_owner == player_index:
            total += 2
        return total

    def public_score(self, player_index: int, viewer_index: int) -> int:
        total = 0
        for b in self.buildings.values():
            if b.owner == player_index:
                total += 2 if b.kind == "city" else 1
        if player_index == viewer_index:
            total += sum(1 for c in self.players[player_index].dev_cards if c == "Victory Point")
        if self.longest_road_owner == player_index:
            total += 2
        if self.largest_army_owner == player_index:
            total += 2
        return total

    def _check_win(self, player_index: int) -> None:
        if self.score(player_index) >= 10:
            self.winner = player_index
            self.add_log(f"{self.players[player_index].name} wins with 10 points!")

    def _update_largest_army(self) -> None:
        best = self.largest_army_owner
        best_count = self.players[best].played_knights if best is not None else 2
        for i, p in enumerate(self.players):
            if p.played_knights >= 3 and p.played_knights > best_count:
                self.largest_army_owner = i
                best_count = p.played_knights

    def _update_longest_road(self) -> None:
        best_owner = self.longest_road_owner
        best_len = self._longest_road_len(best_owner) if best_owner is not None else 4
        for i in range(self.player_count):
            length = self._longest_road_len(i)
            if length >= 5 and length > best_len:
                best_owner = i
                best_len = length
        self.longest_road_owner = best_owner
        if best_owner is not None:
            self._check_win(best_owner)

    def _longest_road_len(self, player_index: int | None) -> int:
        if player_index is None:
            return 0
        graph: dict[int, list[int]] = {}
        player_edges = [e for e, o in self.edges.items() if o == player_index]
        for a, b in player_edges:
            graph.setdefault(a, []).append(b)
            graph.setdefault(b, []).append(a)

        def dfs(v: int, used: set[tuple[int, int]]) -> int:
            best = 0
            for n in graph.get(v, []):
                edge = tuple(sorted((v, n)))
                if edge in used:
                    continue
                block = self.buildings.get(v)
                if block and block.owner != player_index and used:
                    continue
                best = max(best, 1 + dfs(n, used | {edge}))
            return best

        return max((dfs(v, set()) for v in graph), default=0)

    def next_turn(self) -> None:
        p = self.active_player()
        p.new_dev_cards.clear()
        self.current = (self.current + 1) % self.player_count
        self.turn_has_rolled = False
        self.dev_played_this_turn = False
        self.awaiting = None
        self.free_roads_remaining = 0
        self.add_log(f"{self.active_player().name}'s turn.")

    def finish_setup_step(self) -> None:
        self.setup_index += 1
        self.pending_setup_vertex = None
        if self.setup_index >= len(self.setup_order):
            self.phase = "play"
            self.current = 0
            self.add_log("Setup complete. Player 1 begins.")
        else:
            self.current = self.setup_order[self.setup_index]
            self.phase = "setup_settlement"

    def cpu_take_setup(self) -> None:
        pidx = self.current
        vertex = self._cpu_pick_vertex(self.valid_settlement_vertices(pidx, setup=True))
        self.place_settlement(pidx, vertex, setup=True)
        edge = self._cpu_pick_edge(self.valid_road_edges(pidx, setup_vertex=vertex), vertex)
        self.place_road(pidx, edge, setup_vertex=vertex)
        self.finish_setup_step()

    def cpu_take_turn(self) -> None:
        if not self.turn_has_rolled:
            self.roll()
        if self.awaiting == "robber":
            targets = [t.hid for t in self.tiles if not t.robber]
            self.move_robber(random.choice(targets))
        # CPUs trade only with bank and build greedily.
        for _ in range(4):
            self._cpu_trade_for_build()
            if self._cpu_build_city():
                continue
            if self._cpu_build_settlement():
                continue
            if self._cpu_build_road():
                continue
            if self.buy_dev(self.current):
                continue
            break
        playable = self.playable_dev_cards(self.current)
        if playable and random.random() < 0.35:
            self.play_dev(random.choice(playable))
            if self.awaiting == "robber":
                self.move_robber(random.choice([t.hid for t in self.tiles if not t.robber]))
        self.next_turn()

    def _cpu_trade_for_build(self) -> None:
        p = self.active_player()
        for target in ["city", "settlement", "road", "development"]:
            cost = BUILD_COSTS[target]
            missing = [r for r, n in cost.items() if p.resources[r] < n]
            if not missing:
                return
            need = missing[0]
            for give in RESOURCES:
                if give != need and p.resources[give] >= self.trade_rate(self.current, give):
                    self.bank_trade(give, need)
                    return

    def _cpu_build_city(self) -> bool:
        verts = self.valid_city_vertices(self.current)
        return bool(verts and self.place_city(self.current, random.choice(verts)))

    def _cpu_build_settlement(self) -> bool:
        verts = self.valid_settlement_vertices(self.current)
        return bool(verts and self.place_settlement(self.current, self._cpu_pick_vertex(verts)))

    def _cpu_build_road(self) -> bool:
        edges = self.valid_road_edges(self.current)
        return bool(edges and self.place_road(self.current, self._cpu_pick_edge(edges)))

    def _cpu_pick_vertex(self, vertices: list[int]) -> int:
        def value(v: int) -> int:
            total = 0
            for hid in self.vertex_tiles[v]:
                n = self.tiles[hid].number
                if n:
                    total += 6 - abs(7 - n)
            return total
        return max(vertices, key=value)

    def _cpu_pick_edge(self, edges: list[tuple[int, int]], from_vertex: int | None = None) -> tuple[int, int]:
        if from_vertex is not None:
            touching = [e for e in edges if from_vertex in e]
            if touching:
                return random.choice(touching)
        return random.choice(edges)


class CatanApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Settlers Offline")
        self.geometry("1220x820")
        self.minsize(1050, 720)
        self.configure(bg="#f4efe4")
        self.game: CatanGame | None = None
        self.scale = 1.0
        self.offset = (0.0, 0.0)
        self.hover_vertex: int | None = None
        self.selected_action = tk.StringVar(value="inspect")
        self.status = tk.StringVar(value="")
        self.resource_vars: dict[str, tk.StringVar] = {}
        self.score_vars: list[tk.StringVar] = []
        self._show_start()

    def _show_start(self) -> None:
        self._clear()
        frame = ttk.Frame(self, padding=28)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Settlers Offline", font=("Segoe UI", 28, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Local hot-seat play with CPU opponents, 4-player and 6-player boards.", font=("Segoe UI", 12)).pack(anchor="w", pady=(4, 24))
        mode = tk.IntVar(value=4)
        humans = tk.IntVar(value=1)
        names = [tk.StringVar(value=f"Player {i + 1}") for i in range(6)]
        ttk.Label(frame, text="Game Version", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Radiobutton(frame, text="4 players - base board", variable=mode, value=4).pack(anchor="w", pady=2)
        ttk.Radiobutton(frame, text="6 players - extended board", variable=mode, value=6).pack(anchor="w", pady=2)
        ttk.Label(frame, text="Human Players", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(18, 0))
        ttk.Spinbox(frame, from_=1, to=6, textvariable=humans, width=5).pack(anchor="w", pady=4)
        name_frame = ttk.Frame(frame)
        name_frame.pack(anchor="w", pady=(12, 22))
        for i in range(6):
            ttk.Label(name_frame, text=f"Human {i + 1}").grid(row=i, column=0, sticky="w", padx=(0, 8), pady=3)
            ttk.Entry(name_frame, textvariable=names[i], width=24).grid(row=i, column=1, sticky="w", pady=3)

        def start() -> None:
            player_count = mode.get()
            human_count = max(1, min(humans.get(), player_count))
            self.game = CatanGame(player_count, human_count, [n.get() for n in names])
            self._show_game()

        ttk.Button(frame, text="Start Game", command=start).pack(anchor="w", ipadx=12, ipady=5)

    def _show_game(self) -> None:
        self._clear()
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)
        left = ttk.Frame(outer, padding=12, width=260)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        ttk.Label(left, text="Log", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.log_text = tk.Text(left, height=24, wrap="word", state="disabled", bg="#fffaf0")
        self.log_text.pack(fill="both", expand=True, pady=(6, 0))
        self.canvas = tk.Canvas(outer, bg="#77b9d5", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        side = ttk.Frame(outer, padding=10, width=330)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        ttk.Label(side, text="Game", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(side, textvariable=self.status, wraplength=300).pack(anchor="w", pady=(0, 6))
        scores = ttk.LabelFrame(side, text="Scores", padding=8)
        scores.pack(fill="x", pady=(0, 6))
        self.score_vars = [tk.StringVar() for _ in self.game.players]
        for row, var in enumerate(self.score_vars):
            ttk.Label(scores, textvariable=var, font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=1)
        ttk.Label(scores, text="Opponents exclude hidden VP cards.", font=("Segoe UI", 8)).grid(row=len(self.score_vars), column=0, sticky="w", pady=(3, 0))
        button_row = ttk.Frame(side)
        button_row.pack(anchor="w", pady=3)
        ttk.Button(button_row, text="Roll", command=self._roll).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(button_row, text="End Turn", command=self._end_turn).grid(row=0, column=1)
        actions = ttk.LabelFrame(side, text="Action", padding=7)
        actions.pack(fill="x", pady=6)
        for label, action in [
            ("Inspect", "inspect"),
            ("Build Road", "road"),
            ("Build Settlement", "settlement"),
            ("Build City", "city"),
            ("Move Robber", "robber"),
        ]:
            ttk.Radiobutton(actions, text=label, variable=self.selected_action, value=action).pack(anchor="w", pady=0)
        self.selected_action.trace_add("write", lambda *_args: self._redraw())
        ttk.Button(actions, text="Buy Development Card", command=self._buy_dev).pack(fill="x", pady=(8, 2))
        ttk.Button(actions, text="Play Development Card", command=self._play_dev).pack(fill="x", pady=2)
        ttk.Button(actions, text="Build Cost Card", command=self._show_cost_card).pack(fill="x", pady=2)
        trade = ttk.LabelFrame(side, text="Bank / Harbor Trade", padding=7)
        trade.pack(fill="x", pady=6)
        resource_names = [RESOURCE_LABELS[r] for r in RESOURCES]
        give_var = tk.StringVar(value="Brick")
        get_var = tk.StringVar(value="Wood")
        ttk.Combobox(trade, textvariable=give_var, values=resource_names, state="readonly", width=10).grid(row=0, column=0, padx=2)
        ttk.Label(trade, text="for").grid(row=0, column=1, padx=2)
        ttk.Combobox(trade, textvariable=get_var, values=resource_names, state="readonly", width=10).grid(row=0, column=2, padx=2)
        ttk.Button(trade, text="Trade", command=lambda: self._trade(LABEL_TO_RESOURCE[give_var.get()], LABEL_TO_RESOURCE[get_var.get()])).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        ttk.Button(trade, text="Trade With Player", command=self._show_player_trade).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        resources = ttk.LabelFrame(side, text="Resources", padding=7)
        resources.pack(fill="x", pady=6)
        self.resource_vars = {}
        for index, r in enumerate(RESOURCES):
            self.resource_vars[r] = tk.StringVar()
            row = index // 2
            col = (index % 2) * 2
            ttk.Label(resources, text=RESOURCE_LABELS[r]).grid(row=row, column=col, sticky="w", padx=(0, 4), pady=2)
            ttk.Label(resources, textvariable=self.resource_vars[r], font=("Segoe UI", 10, "bold")).grid(row=row, column=col + 1, sticky="w", padx=(0, 18), pady=2)
        ttk.Button(side, text="New Game", command=self._show_start).pack(fill="x", pady=(8, 0))
        self.canvas.bind("<Button-1>", self._click_canvas)
        self.canvas.bind("<Motion>", self._canvas_motion)
        self.canvas.bind("<Leave>", self._canvas_leave)
        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self._after_cpu_if_needed()
        self._refresh()

    def _clear(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def _active_human(self) -> bool:
        return bool(self.game and not self.game.active_player().is_cpu)

    def _after_cpu_if_needed(self) -> None:
        if not self.game or self.game.winner is not None:
            return
        if self.game.active_player().is_cpu:
            self.after(400, self._cpu_step)

    def _cpu_step(self) -> None:
        if not self.game or self.game.winner is not None:
            return
        if self.game.phase.startswith("setup"):
            self.game.cpu_take_setup()
        else:
            self.game.cpu_take_turn()
        self._refresh()
        self._after_cpu_if_needed()

    def _roll(self) -> None:
        if not self._guard_human_turn() or not self.game:
            return
        if self.game.phase != "play":
            messagebox.showinfo("Setup", "Finish setup placements first.")
            return
        if self.game.turn_has_rolled:
            messagebox.showinfo("Roll", "You already rolled this turn.")
            return
        self.game.roll()
        self._refresh()

    def _end_turn(self) -> None:
        if not self._guard_human_turn() or not self.game:
            return
        if self.game.phase != "play":
            messagebox.showinfo("Setup", "Place a settlement and road.")
            return
        if not self.game.turn_has_rolled:
            messagebox.showinfo("Roll first", "Roll before ending your turn.")
            return
        if self.game.awaiting == "robber":
            messagebox.showinfo("Robber", "Move the robber first.")
            return
        if self.game.awaiting == "free_road":
            messagebox.showinfo("Road Building", "Place your free roads first.")
            return
        self.game.next_turn()
        self._refresh()
        self._after_cpu_if_needed()

    def _buy_dev(self) -> None:
        if not self._guard_human_turn() or not self.game:
            return
        if self.game.buy_dev(self.game.current):
            self._refresh()
        else:
            messagebox.showinfo("Development", "You cannot buy a development card right now.")

    def _play_dev(self) -> None:
        if not self._guard_human_turn() or not self.game:
            return
        player = self.game.active_player()
        if not player.dev_cards:
            messagebox.showinfo("Development", "You do not have any development cards.")
            return
        window = tk.Toplevel(self)
        window.title("Development Cards")
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Development Cards", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))
        options = []
        option_cards = []
        playable = self.game.playable_dev_cards(self.game.current)
        new_counts = Counter(player.new_dev_cards)
        for index, card_name in enumerate(player.dev_cards, start=1):
            flags = []
            if new_counts[card_name] > 0:
                flags.append("new this turn")
                new_counts[card_name] -= 1
            if card_name == "Victory Point":
                flags.append("revealed only at scoring")
            if self.game.dev_played_this_turn and card_name != "Victory Point":
                flags.append("already played a card")
            status = f" ({', '.join(flags)})" if flags else " (playable)"
            options.append(f"{index}. {card_name}{status}")
            option_cards.append(card_name)
        selected = tk.StringVar(value=options[0])
        ttk.Combobox(frame, textvariable=selected, values=options, state="readonly", width=46).pack(fill="x")
        ttk.Label(frame, text=f"Playable now: {', '.join(playable) if playable else 'none'}", wraplength=360).pack(anchor="w", pady=(8, 10))

        def play_selected() -> None:
            idx = options.index(selected.get())
            card = option_cards[idx]
            choice = None
            if card == "Monopoly":
                choice = self._choose_resource_dropdown("Monopoly", "Choose the resource to collect.", window)
                if choice is None:
                    return
            elif card == "Year of Plenty":
                choices = self._choose_two_resources_dropdown("Year of Plenty", "Choose two resources to take.", window)
                choice = ",".join(choices) if choices else None
                if choice is None:
                    return
            if self.game.play_dev(card, choice):
                window.destroy()
                self._refresh()
            else:
                messagebox.showinfo("Development", "That card is visible here, but it cannot be played right now.", parent=window)

        ttk.Button(frame, text="Play Selected Card", command=play_selected).pack(fill="x")

    def _choose_resource_dropdown(self, title: str, prompt: str, parent: tk.Toplevel) -> str | None:
        choice_window = tk.Toplevel(parent)
        choice_window.title(title)
        choice_window.resizable(False, False)
        choice_window.transient(parent)
        choice_window.grab_set()
        result: dict[str, str | None] = {"resource": None}
        frame = ttk.Frame(choice_window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=prompt, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        resource_names = [RESOURCE_LABELS[r] for r in RESOURCES]
        selected = tk.StringVar(value=resource_names[0])
        ttk.Combobox(frame, textvariable=selected, values=resource_names, state="readonly", width=18).pack(fill="x")

        def accept() -> None:
            result["resource"] = LABEL_TO_RESOURCE[selected.get()]
            choice_window.destroy()

        ttk.Button(frame, text="Choose", command=accept).pack(fill="x", pady=(10, 0))
        choice_window.wait_window()
        return result["resource"]

    def _choose_two_resources_dropdown(self, title: str, prompt: str, parent: tk.Toplevel) -> list[str] | None:
        choice_window = tk.Toplevel(parent)
        choice_window.title(title)
        choice_window.resizable(False, False)
        choice_window.transient(parent)
        choice_window.grab_set()
        result: dict[str, list[str] | None] = {"resources": None}
        frame = ttk.Frame(choice_window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=prompt, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        resource_names = [RESOURCE_LABELS[r] for r in RESOURCES]
        first = tk.StringVar(value=resource_names[0])
        second = tk.StringVar(value=resource_names[1])
        ttk.Combobox(frame, textvariable=first, values=resource_names, state="readonly", width=18).pack(fill="x", pady=2)
        ttk.Combobox(frame, textvariable=second, values=resource_names, state="readonly", width=18).pack(fill="x", pady=2)

        def accept() -> None:
            result["resources"] = [LABEL_TO_RESOURCE[first.get()], LABEL_TO_RESOURCE[second.get()]]
            choice_window.destroy()

        ttk.Button(frame, text="Choose", command=accept).pack(fill="x", pady=(10, 0))
        choice_window.wait_window()
        return result["resources"]

    def _show_cost_card(self) -> None:
        if not self.game:
            return
        window = tk.Toplevel(self)
        window.title("Build Cost Card")
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Build Costs", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        rows = [
            ("Road", BUILD_COSTS["road"]),
            ("Settlement", BUILD_COSTS["settlement"]),
            ("City", BUILD_COSTS["city"]),
            ("Development Card", BUILD_COSTS["development"]),
        ]
        for row, (name, cost) in enumerate(rows, start=1):
            ttk.Label(frame, text=name, font=("Segoe UI", 11, "bold")).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=4)
            ttk.Label(frame, text=self._format_cost(cost)).grid(row=row, column=1, sticky="w", pady=4)
        ttk.Separator(frame).grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)
        rates = ", ".join(f"{RESOURCE_LABELS[r]} {self.game.trade_rate(self.game.current, r)}:1" for r in RESOURCES)
        ttk.Label(frame, text="Your Bank/Harbor Rates", font=("Segoe UI", 11, "bold")).grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text=rates, wraplength=360).grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _format_cost(self, cost: dict[str, int]) -> str:
        return ", ".join(f"{amount} {RESOURCE_LABELS[resource]}" for resource, amount in cost.items())

    def _show_player_trade(self) -> None:
        if not self._guard_human_turn() or not self.game:
            return
        if self.game.phase != "play" or not self.game.turn_has_rolled:
            messagebox.showinfo("Trade", "Player trades happen after you roll.")
            return
        active = self.game.active_player()
        targets = [i for i in range(self.game.player_count) if i != self.game.current]
        window = tk.Toplevel(self)
        window.title("Trade With Player")
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"{active.name}'s Trade Offer", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        target_var = tk.StringVar(value=self.game.players[targets[0]].name)
        target_names = [self.game.players[i].name for i in targets]
        ttk.Label(frame, text="Trade with").grid(row=1, column=0, sticky="w")
        ttk.Combobox(frame, textvariable=target_var, values=target_names, state="readonly", width=22).grid(row=1, column=1, columnspan=3, sticky="ew", pady=3)
        ttk.Label(frame, text="You Give", font=("Segoe UI", 11, "bold")).grid(row=2, column=1, pady=(10, 4))
        ttk.Label(frame, text="You Get", font=("Segoe UI", 11, "bold")).grid(row=2, column=2, pady=(10, 4))
        offer_vars: dict[str, tk.IntVar] = {}
        request_vars: dict[str, tk.IntVar] = {}
        for offset, resource in enumerate(RESOURCES, start=3):
            ttk.Label(frame, text=RESOURCE_LABELS[resource]).grid(row=offset, column=0, sticky="w", padx=(0, 10), pady=2)
            offer_vars[resource] = tk.IntVar(value=0)
            request_vars[resource] = tk.IntVar(value=0)
            ttk.Spinbox(frame, from_=0, to=20, textvariable=offer_vars[resource], width=5).grid(row=offset, column=1, padx=4, pady=2)
            ttk.Spinbox(frame, from_=0, to=20, textvariable=request_vars[resource], width=5).grid(row=offset, column=2, padx=4, pady=2)
            ttk.Label(frame, text=f"You have {active.resources[resource]}").grid(row=offset, column=3, sticky="w", padx=(10, 0))

        def propose() -> None:
            target_index = next(i for i in targets if self.game.players[i].name == target_var.get())
            offer = {r: max(0, offer_vars[r].get()) for r in RESOURCES}
            request = {r: max(0, request_vars[r].get()) for r in RESOURCES}
            if not any(offer.values()) and not any(request.values()):
                messagebox.showinfo("Trade", "Add at least one resource to the trade.")
                return
            if not self.game._has_resources(active, offer):
                messagebox.showinfo("Trade", "You do not have the resources you are offering.")
                return
            target = self.game.players[target_index]
            if not self.game._has_resources(target, request):
                messagebox.showinfo("Trade", f"{target.name} does not have the requested resources.")
                return
            if target.is_cpu:
                accepted = self._cpu_accepts_trade(target_index, offer, request)
            else:
                accepted = messagebox.askyesno(
                    "Accept Trade?",
                    f"{target.name}, accept this trade?\n\nReceive: {self.game._resource_bundle_text(offer)}\nGive: {self.game._resource_bundle_text(request)}",
                )
            if not accepted:
                self.game.add_log(f"{target.name} declined {active.name}'s trade.")
                self._refresh()
                return
            if self.game.player_trade(self.game.current, target_index, offer, request):
                window.destroy()
                self._refresh()

        ttk.Button(frame, text="Propose Trade", command=propose).grid(row=8, column=0, columnspan=4, sticky="ew", pady=(12, 0))

    def _cpu_accepts_trade(self, cpu_index: int, offer: dict[str, int], request: dict[str, int]) -> bool:
        assert self.game
        cpu = self.game.players[cpu_index]
        if not self.game._has_resources(cpu, request):
            return False
        offer_value = self._trade_bundle_value(cpu_index, offer)
        request_value = self._trade_bundle_value(cpu_index, request)
        current_score = self.game.public_score(self.game.current, cpu_index)
        cpu_score = self.game.public_score(cpu_index, cpu_index)
        leader_penalty = 1.25 if current_score >= cpu_score + 2 else 1.0
        if current_score >= 8:
            leader_penalty += 0.4
        margin = 0.35 + max(0, current_score - cpu_score) * 0.15
        return offer_value >= request_value * leader_penalty + margin

    def _trade_bundle_value(self, player_index: int, bundle: dict[str, int]) -> float:
        assert self.game
        return sum(amount * self._resource_trade_value(player_index, resource) for resource, amount in bundle.items())

    def _resource_trade_value(self, player_index: int, resource: str) -> float:
        assert self.game
        player = self.game.players[player_index]
        value = 1.0
        if player.resources[resource] == 0:
            value += 0.55
        if self.game.trade_rate(player_index, resource) <= 2:
            value -= 0.25
        for build, cost in BUILD_COSTS.items():
            missing = {r: max(0, n - player.resources[r]) for r, n in cost.items()}
            if missing.get(resource, 0) > 0:
                if build == "city" and self.game.valid_city_vertices(player_index):
                    value += 0.9
                elif build == "settlement" and self.game.valid_settlement_vertices(player_index):
                    value += 0.75
                elif build == "road" and self.game.valid_road_edges(player_index):
                    value += 0.35
                elif build == "development":
                    value += 0.25
        return max(0.2, value)

    def _trade(self, give: str, get: str) -> None:
        if not self._guard_human_turn() or not self.game:
            return
        if give == get:
            return
        if not self.game.bank_trade(give, get):
            messagebox.showinfo("Trade", "Not enough resources for that trade.")
        self._refresh()

    def _guard_human_turn(self) -> bool:
        if not self.game or self.game.winner is not None:
            return False
        if self.game.active_player().is_cpu:
            return False
        return True

    def _click_canvas(self, event) -> None:
        if not self._guard_human_turn() or not self.game:
            return
        x = (event.x - self.offset[0]) / self.scale
        y = (event.y - self.offset[1]) / self.scale
        action = self.selected_action.get()
        if self.game.phase.startswith("setup"):
            self._setup_click(x, y)
        elif self.game.awaiting == "free_road":
            edge = self._nearest_edge(x, y)
            if edge is not None and self.game.place_road(self.game.current, edge, free=True):
                self.game.free_roads_remaining -= 1
                if self.game.free_roads_remaining <= 0 or not self.game.valid_road_edges(self.game.current):
                    self.game.awaiting = None
                    self.game.free_roads_remaining = 0
                    self.game.add_log("Road Building complete.")
            else:
                messagebox.showinfo("Road Building", "Choose a legal road edge for your free road.")
        elif self.game.awaiting == "robber" or action == "robber":
            hid = self._nearest_hex(x, y)
            if hid is not None:
                self.game.move_robber(hid)
        elif action == "settlement":
            v = self._nearest_vertex(x, y)
            if v is not None and not self.game.place_settlement(self.game.current, v):
                messagebox.showinfo("Settlement", self.game.settlement_block_reason(self.game.current, v))
            elif v is None:
                messagebox.showinfo("Settlement", self.game.settlement_block_reason(self.game.current, None))
        elif action == "city":
            v = self._nearest_vertex(x, y)
            if v is not None and not self.game.place_city(self.game.current, v):
                messagebox.showinfo("City", "Select one of your settlements and make sure you can afford it.")
        elif action == "road":
            edge = self._nearest_edge(x, y)
            if edge is not None and not self.game.place_road(self.game.current, edge):
                messagebox.showinfo("Road", "That road is not legal or affordable.")
        self._refresh()
        if self.game.winner is not None:
            messagebox.showinfo("Game Over", f"{self.game.players[self.game.winner].name} wins!")

    def _canvas_motion(self, event) -> None:
        if not self.game:
            return
        x = (event.x - self.offset[0]) / self.scale
        y = (event.y - self.offset[1]) / self.scale
        vertex = self._nearest_vertex(x, y)
        if vertex not in self.game.buildings:
            vertex = None
        if vertex != self.hover_vertex:
            self.hover_vertex = vertex
            if vertex is not None:
                self.status.set(self._describe_vertex(vertex))
            else:
                self._refresh_status_only()
            self._redraw()

    def _canvas_leave(self, _event) -> None:
        if self.hover_vertex is not None:
            self.hover_vertex = None
            self._refresh_status_only()
            self._redraw()

    def _describe_vertex(self, vertex: int) -> str:
        assert self.game
        building = self.game.buildings[vertex]
        player = self.game.players[building.owner]
        spots = []
        for hid in self.game.vertex_tiles[vertex]:
            tile = self.game.tiles[hid]
            if tile.terrain == "desert":
                spots.append("Desert")
            else:
                spots.append(f"{TERRAIN_LABELS[tile.terrain]} {tile.number}")
        port = self.game.ports.get(vertex)
        port_text = ""
        if port:
            port_name = "3:1" if port == "3:1" else f"2:1 {RESOURCE_LABELS[port]}"
            port_text = f" | Port: {port_name}"
        return f"{player.name}'s {building.kind}: " + ", ".join(spots) + port_text

    def _setup_click(self, x: float, y: float) -> None:
        assert self.game
        if self.game.phase == "setup_settlement":
            v = self._nearest_vertex(x, y)
            if v is not None and self.game.place_settlement(self.game.current, v, setup=True):
                self.game.pending_setup_vertex = v
                self.game.phase = "setup_road"
            else:
                messagebox.showinfo("Setup", "Choose an open intersection at least two edges away from another settlement.")
        elif self.game.phase == "setup_road":
            edge = self._nearest_edge(x, y)
            if edge is not None and self.game.place_road(self.game.current, edge, setup_vertex=self.game.pending_setup_vertex):
                self.game.finish_setup_step()
                self._after_cpu_if_needed()
            else:
                messagebox.showinfo("Setup", "Choose an open road touching the settlement you just placed.")

    def _nearest_vertex(self, x: float, y: float) -> int | None:
        assert self.game
        best = min(self.game.vertices, key=lambda v: (self.game.vertices[v][0] - x) ** 2 + (self.game.vertices[v][1] - y) ** 2)
        bx, by = self.game.vertices[best]
        return best if math.hypot(bx - x, by - y) < 20 else None

    def _nearest_hex(self, x: float, y: float) -> int | None:
        assert self.game
        centers = {t.hid: self._hex_center(t.q, t.r) for t in self.game.tiles}
        best = min(centers, key=lambda h: (centers[h][0] - x) ** 2 + (centers[h][1] - y) ** 2)
        return best

    def _nearest_edge(self, x: float, y: float) -> tuple[int, int] | None:
        assert self.game
        def dist(edge):
            a, b = edge
            ax, ay = self.game.vertices[a]
            bx, by = self.game.vertices[b]
            px, py = self._project_point(x, y, ax, ay, bx, by)
            return (px - x) ** 2 + (py - y) ** 2
        best = min(self.game.edges, key=dist)
        return best if math.sqrt(dist(best)) < 18 else None

    def _project_point(self, px, py, ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return ax, ay
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return ax + t * dx, ay + t * dy

    def _hex_center(self, q: float, r: int, size: float = 46) -> tuple[float, float]:
        return size * math.sqrt(3) * (q + r / 2), size * 1.5 * r

    def _redraw(self) -> None:
        if not self.game:
            return
        self.canvas.delete("all")
        xs = [p[0] for p in self.game.vertices.values()]
        ys = [p[1] for p in self.game.vertices.values()]
        w, h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        board_w = max(xs) - min(xs) + 160
        board_h = max(ys) - min(ys) + 160
        self.scale = min(w / board_w, h / board_h)
        self.offset = (w / 2 - self.scale * (min(xs) + max(xs)) / 2, h / 2 - self.scale * (min(ys) + max(ys)) / 2)
        for tile in self.game.tiles:
            points = [self._screen(*self.game.vertices[v]) for v in tile.vertices]
            flat = [coord for p in points for coord in p]
            self.canvas.create_polygon(flat, fill=TERRAIN_COLORS[tile.terrain], outline="#35545e", width=2)
            cx, cy = self._screen(*self._hex_center(tile.q, tile.r))
            self.canvas.create_text(cx, cy - 12, text=TERRAIN_LABELS[tile.terrain], fill="white" if tile.terrain in ("forest", "hills", "mountains") else "#2b2b2b", font=("Segoe UI", 10, "bold"))
            if tile.number:
                color = "#b21f24" if tile.number in (6, 8) else "#222"
                self.canvas.create_oval(cx - 18, cy + 2, cx + 18, cy + 42, fill="#f7efd5", outline="#5c4934")
                self.canvas.create_text(cx, cy + 15, text=str(tile.number), fill=color, font=("Segoe UI", 12, "bold"))
                dots = NUMBER_DOTS[tile.number]
                dot_spacing = 5
                start_x = cx - ((dots - 1) * dot_spacing / 2)
                for dot in range(dots):
                    dx = start_x + dot * dot_spacing
                    self.canvas.create_oval(dx - 1.6, cy + 29, dx + 1.6, cy + 32.2, fill=color, outline=color)
            if tile.robber:
                self.canvas.create_oval(cx - 11, cy - 33, cx + 11, cy - 11, fill="#1f1f1f", outline="#000")
                self.canvas.create_rectangle(cx - 8, cy - 13, cx + 8, cy + 7, fill="#1f1f1f", outline="#000")
        if self.hover_vertex is not None:
            for hid in self.game.vertex_tiles[self.hover_vertex]:
                tile = self.game.tiles[hid]
                points = [self._screen(*self.game.vertices[v]) for v in tile.vertices]
                flat = [coord for p in points for coord in p]
                self.canvas.create_polygon(flat, fill="#fff6a6", outline="#f5d547", width=3, stipple="gray25")
        for edge, owner in self.game.edges.items():
            if owner is None:
                continue
            a, b = edge
            ax, ay = self._screen(*self.game.vertices[a])
            bx, by = self._screen(*self.game.vertices[b])
            self.canvas.create_line(ax, ay, bx, by, fill=self.game.players[owner].color, width=6, capstyle="round")
        for v, _partner, port in self.game.port_markers:
            vx, vy = self.game.vertices[v]
            x, y = self._screen(vx, vy)
            label = "3" if port == "3:1" else RESOURCE_LABELS[port][:2].lower()
            self.canvas.create_oval(x - 14, y - 14, x + 14, y + 14, fill="#e8f2ff", outline="#225d78", width=2)
            self.canvas.create_text(x, y, text=label, font=("Segoe UI", 8, "bold"))
        if self.selected_action.get() == "settlement" and self.game.phase == "play" and not self.game.active_player().is_cpu:
            legal = self.game.valid_settlement_vertices(self.game.current)
            for v in legal:
                x, y = self._screen(*self.game.vertices[v])
                self.canvas.create_oval(x - 9, y - 9, x + 9, y + 9, fill="#f9ff8a", outline="#111", width=2, stipple="gray50")
        for v, building in self.game.buildings.items():
            x, y = self._screen(*self.game.vertices[v])
            color = self.game.players[building.owner].color
            if building.kind == "city":
                self.canvas.create_rectangle(x - 11, y - 13, x + 13, y + 11, fill=color, outline="#222", width=2)
                self.canvas.create_rectangle(x + 4, y - 22, x + 17, y + 11, fill=color, outline="#222", width=2)
                if v == self.hover_vertex:
                    self.canvas.create_rectangle(x - 15, y - 17, x + 21, y + 15, fill="#ffffff", outline="#f5d547", width=3, stipple="gray50")
            else:
                self.canvas.create_polygon(x - 12, y + 10, x - 12, y - 4, x, y - 15, x + 12, y - 4, x + 12, y + 10, fill=color, outline="#222", width=2)
                if v == self.hover_vertex:
                    self.canvas.create_polygon(x - 16, y + 14, x - 16, y - 6, x, y - 21, x + 16, y - 6, x + 16, y + 14, fill="#ffffff", outline="#f5d547", width=3, stipple="gray50")

    def _screen(self, x: float, y: float) -> tuple[float, float]:
        return x * self.scale + self.offset[0], y * self.scale + self.offset[1]

    def _refresh_status_only(self) -> None:
        if not self.game:
            return
        p = self.game.active_player()
        if self.game.phase == "setup_settlement":
            prompt = f"{p.name}: place a starting settlement."
        elif self.game.phase == "setup_road":
            prompt = f"{p.name}: place a road touching that settlement."
        elif self.game.awaiting == "robber":
            prompt = f"{p.name}: move the robber."
            self.selected_action.set("robber")
        elif self.game.awaiting == "free_road":
            prompt = f"{p.name}: place {self.game.free_roads_remaining} free road{'s' if self.game.free_roads_remaining != 1 else ''}."
            self.selected_action.set("road")
        else:
            prompt = f"{p.name}'s turn. " + ("Roll the dice." if not self.game.turn_has_rolled else "Trade, build, play a card, or end turn.")
        if self.game.winner is not None:
            prompt = f"{self.game.players[self.game.winner].name} wins."
        self.status.set(prompt)

    def _refresh(self) -> None:
        if not self.game:
            return
        self._refresh_status_only()
        p = self.game.active_player()
        for r, var in self.resource_vars.items():
            var.set(str(p.resources[r]))
        for i, var in enumerate(self.score_vars):
            player = self.game.players[i]
            cpu = " (CPU)" if player.is_cpu else ""
            awards = []
            if self.game.longest_road_owner == i:
                awards.append("LR")
            if self.game.largest_army_owner == i:
                awards.append("LA")
            suffix = f" [{', '.join(awards)}]" if awards else ""
            score = self.game.public_score(i, self.game.current)
            name = player.name
            if len(name) > 14:
                name = name[:13] + "."
            var.set(f"{name}{cpu}: {score} VP{suffix}")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "\n".join(self.game.log[-16:]))
        self.log_text.configure(state="disabled")
        self._redraw()


if __name__ == "__main__":
    CatanApp().mainloop()
