import random
from collections import defaultdict, Counter
from itertools import combinations


class ComprehensiveBlockGenerator:
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
        return rooms

    def _generate_all_possible_blocks(self, available_rooms):
        """Generate all physically possible blocks"""
        blocks = []
        by_type = defaultdict(list)

        for room in available_rooms:
            by_type[room["type"]].append(room)

        # Generate all possible multi-room blocks (same type)
        for room_type, rooms in by_type.items():
            # All horizontal combinations
            for r in range(2, len(rooms) + 1):
                for combo in combinations(rooms, r):
                    if all(r['height'] == combo[0]['height'] for r in combo):
                        blocks.append({
                            "width": sum(r['width'] for r in combo),
                            "height": combo[0]['height'],
                            "rooms": list(combo),
                            "room_types": [room_type],
                            "room_ids": {r['id'] for r in combo}
                        })

            # All vertical combinations
            for r in range(2, len(rooms) + 1):
                for combo in combinations(rooms, r):
                    if all(r['width'] == combo[0]['width'] for r in combo):
                        blocks.append({
                            "width": combo[0]['width'],
                            "height": sum(r['height'] for r in combo),
                            "rooms": list(combo),
                            "room_types": [room_type],
                            "room_ids": {r['id'] for r in combo}
                        })

        # Add all single-room blocks
        for room in available_rooms:
            blocks.append({
                "width": room["width"],
                "height": room["height"],
                "rooms": [room],
                "room_types": [room["type"]],
                "room_ids": {room["id"]}
            })

        return blocks

    def _find_configurations(self, max_configs=100):
        """Find all possible configurations up to max_configs"""
        all_configs = []
        blocks = self._generate_all_possible_blocks(self.rooms)

        # We'll use a stack to keep track of partial configurations
        stack = [([], set(r['id'] for r in self.rooms))]

        while stack and len(all_configs) < max_configs:
            current_config, remaining_rooms = stack.pop()

            if not remaining_rooms:
                # Found a complete configuration
                all_configs.append(current_config)
                continue

            # Find all possible blocks that can be added
            possible_blocks = [
                b for b in blocks
                if b["room_ids"].issubset(remaining_rooms)
            ]

            # Try blocks from largest to smallest
            possible_blocks.sort(key=lambda b: (-len(b["rooms"]), b["width"] * b["height"]))

            for block in possible_blocks[:100]:  # Limit to top 100 possibilities per step
                new_config = current_config + [block]
                new_remaining = remaining_rooms - block["room_ids"]
                stack.append((new_config, new_remaining))

        return all_configs

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
            print(f"  Rooms: {[r['id'] for r in sorted(block['rooms'], key=lambda x: x['id'])]}")

if __name__ == "__main__":
    room_defs = [
                {"type": "Bedroom", "width": 3, "height": 3, "count": 10},
                {"type": "Kitchen", "width": 4, "height": 3, "count": 7},
                {"type": "Bathroom", "width": 2, "height": 2, "count": 6},
                {"type": "Living", "width": 5, "height": 4, "count": 5}
    ]

    print("=== Comprehensive Block Generator ===")
    print(f"Total rooms defined: {sum(r['count'] for r in room_defs)}")

    try:
        generator = ComprehensiveBlockGenerator(room_defs)
        print("\nGenerating configurations...")
        configurations = generator._find_configurations(100)

        # Sort configurations by number of blocks (smallest first)
        configurations.sort(key=lambda c: len(c))

        print(f"\nGenerated {len(configurations)} configurations")
        for i, config in enumerate(configurations[:100], 1):  # Show first 100
            generator.print_configuration(config, i)

    except Exception as e:
        print(f"\nError: {str(e)}")