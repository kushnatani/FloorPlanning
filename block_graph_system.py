import itertools
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Set, Iterator
import copy


class RoomType:
    """Represents a type of room with its dimensions, including potential orientation."""

    def __init__(self, name: str, width: int, height: int, original_name: str = None, is_rotated: bool = False):
        self.name = name  # e.g., "Bedroom_5x4" or "Bedroom_4x5"
        self.original_name = original_name if original_name is not None else name  # e.g., "Bedroom"
        self.width = width
        self.height = height
        self.area = width * height
        self.is_rotated = is_rotated  # True if this specific RoomType instance represents a rotated version

    def __repr__(self):
        orientation_info = " (Rotated)" if self.is_rotated else ""
        return f"RoomType({self.original_name}_{self.width}x{self.height}{orientation_info})"

    def __eq__(self, other):
        # Equality based on original name and current dimensions
        return (isinstance(other, RoomType) and
                self.original_name == other.original_name and
                self.width == other.width and
                self.height == other.height)

    def __hash__(self):
        return hash((self.original_name, self.width, self.height))


class Block:
    """Represents a rectangular block made of multiple rooms"""

    def __init__(self, rooms: List[RoomType], arrangement: Tuple[int, int]):
        self.rooms = rooms  # List of RoomType instances in this block
        self.arrangement = arrangement  # (rows, cols) arrangement
        # Use original_name for composition tracking for inventory matching
        self.room_composition = Counter(room.original_name for room in rooms)
        self.total_area = sum(room.area for room in rooms)
        self.block_width = 0
        self.block_height = 0
        self._calculate_dimensions()

    def _calculate_dimensions(self):
        """Calculate block dimensions based on room arrangement"""
        if not self.rooms:
            return

        rows, cols = self.arrangement
        if len(self.rooms) != rows * cols:
            raise ValueError("Number of rooms doesn't match arrangement")

        # This part still assumes rooms within a block are of uniform dimensions
        # or that their dimensions align perfectly for a simple grid calculation.
        # For true arbitrary packing with rotation, this method would need a full
        # 2D bin packing algorithm.
        # Given the current simple grid arrangement, we will base it on the first room.
        # If rooms within a block have different dimensions, this needs to be re-evaluated.
        sample_room = self.rooms[0]
        self.block_width = cols * sample_room.width
        self.block_height = rows * sample_room.height

    def can_be_made_from_inventory(self, inventory: Dict[str, int]) -> int:
        """Returns maximum number of this block type that can be made from inventory.
           Inventory should use original room names (e.g., "Bedroom" not "Bedroom_5x4")."""
        if not self.room_composition:
            return 0

        max_blocks = float('inf')
        for original_room_name, count_needed in self.room_composition.items():
            if original_room_name not in inventory or inventory[original_room_name] < count_needed:
                return 0  # Not enough rooms
            max_blocks = min(max_blocks, inventory[original_room_name] // count_needed)

        return int(max_blocks) if max_blocks != float('inf') else 0

    def __repr__(self):
        composition_str = ", ".join(f"{count}x{name}" for name, count in self.room_composition.items())
        return f"Block({composition_str}, {self.arrangement[0]}x{self.arrangement[1]}, area={self.total_area})"

    def __eq__(self, other):
        return (isinstance(other, Block) and
                self.room_composition == other.room_composition and
                self.arrangement == other.arrangement and
                self.block_width == other.block_width and  # Added for better distinction of block dimensions
                self.block_height == other.block_height)

    def __hash__(self):
        return hash((frozenset(self.room_composition.items()), self.arrangement, self.block_width, self.block_height))


class GraphConfiguration:
    """Represents a complete graph configuration with multiple block types"""

    def __init__(self, block_counts: Dict[Block, int]):
        # Filter out blocks with count 0
        self.block_counts = {block: count for block, count in block_counts.items() if count > 0}
        self.total_blocks = sum(self.block_counts.values())

        # Calculate total rooms based on the final block_counts
        self.total_rooms_in_graph = sum(
            block.room_composition.get(room_name, 0) * block_count  # Use .get for robustness
            for block, block_count in self.block_counts.items()
            for room_name in block.room_composition
        )

    def get_room_usage(self) -> Dict[str, int]:
        """Get total room usage across all blocks. Returns counts by original room name."""
        room_usage = defaultdict(int)
        for block, block_count in self.block_counts.items():
            for room_original_name, room_count_in_block in block.room_composition.items():
                room_usage[room_original_name] += room_count_in_block * block_count
        return dict(room_usage)

    def __repr__(self):
        block_strs = [f"{count}x{block}" for block, count in self.block_counts.items() if count > 0]
        return f"Graph({', '.join(block_strs)})"

    def __eq__(self, other):
        # Compare based on the block_counts dictionary
        if not isinstance(other, GraphConfiguration):
            return NotImplemented
        return self.block_counts == other.block_counts

    def __hash__(self):
        # Convert block_counts to a frozenset of (hash(block), count) tuples for hashing
        # This handles the case where Block objects are unique instances but represent the same block type
        return hash(frozenset((hash(block), count) for block, count in self.block_counts.items()))


class BlockGraphGenerator:
    """Main class for generating all possible block types and graph configurations"""

    def __init__(self, room_inventory: Dict[str, Tuple[int, Tuple[int, int]]]):
        """
        Initialize with room inventory.
        room_inventory: {original_room_name: (count, (width, height))}
        """
        self.original_room_specs = room_inventory
        self.room_counts = {name: count for name, (count, dims) in room_inventory.items()}

        # Generate all possible RoomType instances, including rotated versions
        self.available_room_types = self._generate_all_room_orientations()
        self._all_generated_block_types: List[Block] = []  # Cache for all block types, sorted
        self._generated_graphs_cache: Set[GraphConfiguration] = set()  # Cache for unique graphs already yielded

    def _generate_all_room_orientations(self) -> Dict[str, RoomType]:
        """Generates RoomType instances for all original and rotated orientations."""
        room_types_by_name = {}
        for name, (count, (width, height)) in self.original_room_specs.items():
            # Original orientation
            key_original = f"{name}_{width}x{height}"
            room_types_by_name[key_original] = RoomType(key_original, width, height, original_name=name,
                                                        is_rotated=False)

            # Rotated orientation (if different from original)
            if width != height:
                key_rotated = f"{name}_{height}x{width}"
                room_types_by_name[key_rotated] = RoomType(key_rotated, height, width, original_name=name,
                                                           is_rotated=True)
        return room_types_by_name

    def generate_all_block_types(self, max_block_size: int = 8) -> List[Block]:
        """Generate all possible block types from available rooms, considering orientations."""
        if self._all_generated_block_types:
            return self._all_generated_block_types  # Return cached blocks if already generated

        all_blocks = []
        room_type_keys = list(self.available_room_types.keys())

        for total_rooms_in_block in range(1, max_block_size + 1):
            arrangements = [(r, c) for r in range(1, total_rooms_in_block + 1)
                            for c in range(1, total_rooms_in_block + 1) if r * c == total_rooms_in_block]

            for arrangement in arrangements:
                for room_combination_keys in itertools.combinations_with_replacement(room_type_keys,
                                                                                     total_rooms_in_block):
                    rooms = [self.available_room_types[key] for key in room_combination_keys]

                    if not rooms:
                        continue
                    # Check if all rooms in this proposed block have matching dimensions for a simple grid
                    if not all(r.width == rooms[0].width and r.height == rooms[0].height for r in rooms):
                        continue

                    try:
                        block = Block(rooms, arrangement)
                        if block.can_be_made_from_inventory(self.room_counts) > 0:
                            all_blocks.append(block)
                    except ValueError:
                        continue

        unique_blocks = list(set(all_blocks))
        # Sort by total area (largest first), then by number of rooms
        unique_blocks.sort(key=lambda b: (-b.total_area, -len(b.rooms)))

        self._all_generated_block_types = unique_blocks
        return unique_blocks

    def _find_valid_block_assignments_list(self, blocks: Tuple[Block, ...]) -> List[GraphConfiguration]:
        """
        Recursive backtracking function to find all valid ways to assign counts to a set of block types.
        Returns a list of GraphConfiguration objects.
        """
        valid_graphs = []

        def backtrack_list(block_index: int, current_assignment: Dict[Block, int], remaining_inventory: Dict[str, int]):
            if block_index == len(blocks):
                if any(count > 0 for count in current_assignment.values()):
                    valid_graphs.append(GraphConfiguration(current_assignment.copy()))
                return

            current_block = blocks[block_index]
            max_possible = current_block.can_be_made_from_inventory(remaining_inventory)

            for count in range(max_possible + 1):
                current_assignment[current_block] = count
                new_inventory = remaining_inventory.copy()
                for room_name, room_count in current_block.room_composition.items():
                    new_inventory[room_name] -= room_count * count
                backtrack_list(block_index + 1, current_assignment, new_inventory)

        backtrack_list(0, {}, self.room_counts.copy())
        return valid_graphs

    def generate_all_graph_configurations(self, max_block_types: int = 5) -> List[GraphConfiguration]:
        """
        Generates ALL possible graph configurations and returns them as a sorted list.
        This is the original full generation method, useful for analysis.
        """
        all_blocks = self.generate_all_block_types()
        all_graphs = []

        # Start with largest blocks and work down
        for num_block_types in range(1, min(max_block_types + 1, len(all_blocks) + 1)):
            for block_combination in itertools.combinations(all_blocks, num_block_types):
                valid_graphs = self._find_valid_block_assignments_list(block_combination)
                all_graphs.extend(valid_graphs)

        unique_graphs = list(set(all_graphs))
        unique_graphs.sort(key=lambda g: (-sum(block.total_area * count for block, count in g.block_counts.items())))

        return unique_graphs

    def yield_graph_configurations(self, max_block_types: int = 5) -> Iterator[GraphConfiguration]:
        """
        Yields graph configurations one by one, allowing for on-demand generation.
        It prioritizes graphs made with larger blocks first by iterating through sorted blocks.
        """
        all_blocks = self.generate_all_block_types()  # Ensures blocks are generated and sorted

        # This set tracks graphs yielded by *this specific generator invocation*
        # to prevent duplicates if the backtracking yields the same configuration via different paths.
        already_yielded_graphs_for_this_invocation: Set[GraphConfiguration] = set()

        def _backtrack_and_yield_internal(block_index: int, current_assignment: Dict[Block, int],
                                          remaining_inventory: Dict[str, int], blocks_to_consider: Tuple[Block, ...]):
            """Internal recursive function to yield valid assignments."""
            if block_index == len(blocks_to_consider):
                if any(count > 0 for count in current_assignment.values()):
                    graph = GraphConfiguration(current_assignment.copy())
                    # Only yield if this specific graph configuration hasn't been yielded yet in this call
                    if graph not in already_yielded_graphs_for_this_invocation:
                        already_yielded_graphs_for_this_invocation.add(graph)
                        yield graph
                return

            current_block = blocks_to_consider[block_index]
            max_possible = current_block.can_be_made_from_inventory(remaining_inventory)

            for count in range(max_possible + 1):
                temp_assignment = current_assignment.copy()  # Use a copy for this level of recursion
                temp_assignment[current_block] = count

                new_inventory = remaining_inventory.copy()
                for room_name, room_count in current_block.room_composition.items():
                    new_inventory[room_name] -= room_count * count

                yield from _backtrack_and_yield_internal(block_index + 1, temp_assignment, new_inventory,
                                                         blocks_to_consider)

        # Iterate through combinations of block types.
        # `all_blocks` is already sorted by area (largest first).
        # `itertools.combinations` will pick combinations in a lexicographical order,
        # but because `all_blocks` is sorted, combinations involving larger blocks will generally
        # appear earlier or be composed of larger-area blocks.
        for num_block_types in range(1, max_block_types + 1):
            for block_combination in itertools.combinations(all_blocks, num_block_types):
                yield from _backtrack_and_yield_internal(0, {}, self.room_counts.copy(), block_combination)

    def print_summary(self, graphs: List[GraphConfiguration], max_display: int = 20):
        """Print summary of generated graphs"""
        print(f"\n=== Block Graph Generation Summary ===")
        print(f"Total room inventory: {self.room_counts}")
        print(f"Generated {len(graphs)} unique graph configurations")

        print(f"\nTop {min(max_display, len(graphs))} configurations:")
        for i, graph in enumerate(graphs[:max_display]):
            print(f"\n{i + 1}. {graph}")
            room_usage = graph.get_room_usage()
            print(f"   Room usage (original names): {room_usage}")

            # Calculate efficiency
            total_available = sum(self.room_counts.values())
            total_used = sum(room_usage.values())
            efficiency = (total_used / total_available) * 100 if total_available > 0 else 0
            print(f"   Efficiency: {efficiency:.1f}% ({total_used}/{total_available} rooms used)")


# Example usage and testing
def main():
    # Define inventory: original_room_name -> (count, (width, height))
    room_inventory = {
        "LivingRoom": (5, (8, 4)),
        "Kitchen": (8, (6, 4)),
        "Bedroom": (12, (5, 4)),
        "Bathroom": (6, (3, 4)),
        "Office": (4, (4, 3))
    }

    # Create generator
    generator = BlockGraphGenerator(room_inventory)

    # Pre-generate all possible block types (this will also cache them internally and sort)
    print("Pre-generating all possible block types (considering rotations)...")
    all_blocks = generator.generate_all_block_types(max_block_size=4)  # max_block_size for individual blocks
    print(f"Finished pre-generating {len(all_blocks)} block types.")

    print("\n--- Generating graphs one by one using the yield_graph_configurations generator ---")

    # Get a generator object
    graph_iterator = generator.yield_graph_configurations(max_block_types=3)  # max_block_types for graph composition

    # Simulate "hitting a button" to get the next graph
    try:
        print("\nFirst Graph (on 'button hit 1'):")
        first_graph = next(graph_iterator)
        print(first_graph)
        print(f"   Room usage: {first_graph.get_room_usage()}")
        total_available = sum(generator.room_counts.values())
        total_used = sum(first_graph.get_room_usage().values())
        efficiency = (total_used / total_available) * 100 if total_available > 0 else 0
        print(f"   Efficiency: {efficiency:.1f}%")

        print("\nSecond Graph (on 'button hit 2'):")
        second_graph = next(graph_iterator)
        print(second_graph)
        print(f"   Room usage: {second_graph.get_room_usage()}")
        total_available = sum(generator.room_counts.values())
        total_used = sum(second_graph.get_room_usage().values())
        efficiency = (total_used / total_available) * 100 if total_available > 0 else 0
        print(f"   Efficiency: {efficiency:.1f}%")

        print("\nThird Graph (on 'button hit 3'):")
        third_graph = next(graph_iterator)
        print(third_graph)
        print(f"   Room usage: {third_graph.get_room_usage()}")
        total_available = sum(generator.room_counts.values())
        total_used = sum(third_graph.get_room_usage().values())
        efficiency = (total_used / total_available) * 100 if total_available > 0 else 0
        print(f"   Efficiency: {efficiency:.1f}%")

        # You can continue calling next(graph_iterator) to get more graphs
        # until StopIteration is raised, indicating no more unique configurations.

    except StopIteration:
        print("\nNo more graph configurations to generate from the current parameters.")

    print("\n--- Demonstrating original 'generate_all_graph_configurations' for comparison ---")
    all_graphs = generator.generate_all_graph_configurations(max_block_types=3)
    generator.print_summary(all_graphs, max_display=15)


if __name__ == "__main__":
    main()