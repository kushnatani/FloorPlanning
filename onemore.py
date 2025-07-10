import sys
from collections import defaultdict, Counter
from itertools import combinations


class FinalBlockGenerator:
    def __init__(self, room_definitions):
        self.room_definitions = room_definitions
        self.rooms = self._expand_rooms()
        self.room_map = {r['id']: r for r in self.rooms}

        # Validate input
        if len(self.rooms) != sum(r["count"] for r in room_definitions):
            raise ValueError("Room count mismatch in definitions")

    def _expand_rooms(self):
        """Create individual room objects with unique IDs"""
        rooms = []
        for room_type in self.room_definitions:
            for i in range(1, room_type["count"] + 1):
                rooms.append({
                    "id": f"{room_type['type']}_{i}",
                    "type": room_type["type"],
                    "width": room_type["width"],
                    "height": room_type["height"]
                })
        return sorted(rooms, key=lambda x: x['id'])  # Sort by ID initially

    def _generate_blocks_for_type(self, rooms):
        """Generate all possible blocks for rooms of the same type"""
        blocks = []

        # Single room blocks
        for room in rooms:
            blocks.append({
                "width": room["width"],
                "height": room["height"],
                "rooms": [room],
                "room_ids": {room["id"]}
            })

        # Horizontal combinations (same height)
        if len(rooms) > 1:
            same_height = defaultdict(list)
            for room in rooms:
                same_height[room["height"]].append(room)

            for height, group in same_height.items():
                if len(group) > 1:
                    # Try all possible combinations
                    for r in range(2, len(group) + 1):
                        for combo in combinations(group, r):
                            blocks.append({
                                "width": sum(r['width'] for r in combo),
                                "height": height,
                                "rooms": list(combo),
                                "room_ids": {r['id'] for r in combo}
                            })

        # Vertical combinations (same width)
        if len(rooms) > 1:
            same_width = defaultdict(list)
            for room in rooms:
                same_width[room["width"]].append(room)

            for width, group in same_width.items():
                if len(group) > 1:
                    # Try all possible combinations
                    for r in range(2, len(group) + 1):
                        for combo in combinations(group, r):
                            blocks.append({
                                "width": width,
                                "height": sum(r['height'] for r in combo),
                                "rooms": list(combo),
                                "room_ids": {r['id'] for r in combo}
                            })

        # Sort by number of rooms (largest first)
        return sorted(blocks, key=lambda b: (-len(b["rooms"]), b["width"], b["height"]))

    def _find_configurations(self, max_configs=100):
        """Find configurations with minimal blocks first, no duplicates"""
        # Group rooms by type
        by_type = defaultdict(list)
        for room in self.rooms:
            by_type[room["type"]].append(room)

        # Generate all possible blocks for each room type
        type_blocks = {}
        for room_type, rooms in by_type.items():
            type_blocks[room_type] = self._generate_blocks_for_type(rooms)

        # We'll use backtracking to find combinations of blocks that cover all rooms
        all_configs = []
        room_ids = {r['id'] for r in self.rooms}

        def backtrack(current_config, remaining_rooms, current_blocks):
            if not remaining_rooms:
                # Found a valid configuration
                config_key = frozenset(
                    (block["width"], block["height"], frozenset(block["room_ids"]))
                    for block in current_config
                )
                if config_key not in seen_configs:
                    seen_configs.add(config_key)
                    all_configs.append(current_config.copy())
                return

            if len(all_configs) >= max_configs:
                return

            # Try each possible block that covers some remaining rooms
            for room_type in list(current_blocks.keys()):
                if not current_blocks[room_type]:
                    continue

                block = current_blocks[room_type].pop(0)

                if block["room_ids"].issubset(remaining_rooms):
                    current_config.append(block)
                    backtrack(
                        current_config,
                        remaining_rooms - block["room_ids"],
                        current_blocks.copy()
                    )
                    current_config.pop()

                # Put the block back for other possibilities
                current_blocks[room_type].append(block)

        seen_configs = set()
        initial_blocks = {
            room_type: sorted(blocks, key=lambda b: (-len(b["rooms"]), b["width"], b["height"]))
            for room_type, blocks in type_blocks.items()
        }

        backtrack([], room_ids.copy(), initial_blocks)

        # Sort configurations by number of blocks
        return sorted(all_configs, key=lambda c: len(c))

    def print_configuration(self, config, config_num=None):
        """Print a configuration in readable format"""
        if config_num is not None:
            print(f"\nConfiguration {config_num}:")
        print(f"Total blocks: {len(config)}, Rooms: {sum(len(b['rooms']) for b in config)}")
        for i, block in enumerate(config):
            room_types = Counter(r['type'] for r in block['rooms'])
            type_desc = ", ".join([f"{count} {typ}{'s' if count > 1 else ''}"
                                   for typ, count in room_types.items()])
            print(f"  Block {i + 1}: {block['width']}x{block['height']} ({type_desc})")
            print(f"      Rooms: {sorted(r['id'] for r in block['rooms'])}")


if __name__ == "__main__":
    room_defs = [
        {"type": "Bedroom", "width": 3, "height": 3, "count": 4},
        {"type": "Kitchen", "width": 4, "height": 3, "count": 1},
        {"type": "Bathroom", "width": 2, "height": 2, "count": 2},
        {"type": "Living", "width": 5, "height": 4, "count": 1}
    ]

    print("=== Final Block Generator ===")
    print(f"Total rooms defined: {sum(r['count'] for r in room_defs)}")

    try:
        generator = FinalBlockGenerator(room_defs)
        print("\nGenerating unique configurations (minimal blocks first)...")
        configurations = generator._find_configurations(100)

        print(f"\nGenerated {len(configurations)} unique configurations")
        for i, config in enumerate(configurations[:100], 1):
            generator.print_configuration(config, i)

    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)