import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from neg3 import FloorPlan  # Import from your original file
import json
from tkinter import filedialog
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches


class FloorPlanGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Floor Plan Designer")
        self.root.geometry("1200x800")

        # Initialize floor plan with example data
        self.floor_plan = None
        self.current_screen = "regions"

        # Create main container
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create navigation frame
        self.nav_frame = ttk.Frame(self.main_frame)
        self.nav_frame.pack(fill=tk.X, pady=(0, 10))

        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("Region Specs", "regions"),
            ("Rooms", "rooms"),
            ("Adjacency", "adjacency"),
            ("Non-Adjacency", "non_adjacency"),  # Added this line
            ("Output", "output")
        ]

        for i, (text, screen) in enumerate(nav_items):
            btn = ttk.Button(self.nav_frame, text=text,
                             command=lambda s=screen: self.show_screen(s))
            btn.pack(side=tk.LEFT, padx=5)
            self.nav_buttons[screen] = btn

        # Generate button
        ttk.Button(self.nav_frame, text="Generate Floor Plan",
                   command=self.generate_floor_plan,
                   style="Accent.TButton").pack(side=tk.RIGHT, padx=5)

        # Create content frame
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Initialize screens
        self.screens = {}
        self.init_screens()

        # Load example data
        self.load_example_data()

        # Show initial screen
        self.show_screen("regions")

    def init_screens(self):
        """Initialize all screen frames"""
        # Region Specs Screen
        self.init_regions_screen()

        # Rooms Screen
        self.init_rooms_screen()

        # Adjacency Screen
        self.init_adjacency_screen()

        # Non-Adjacency Screen
        self.init_non_adjacency_screen()

        # Output Screen
        self.init_output_screen()

    def init_regions_screen(self):
        """Initialize the region specifications screen"""
        frame = ttk.Frame(self.content_frame)
        self.screens["regions"] = frame

        # Title
        ttk.Label(frame, text="Floor Region Specifications",
                  font=("Arial", 16, "bold")).pack(pady=(0, 20))

        # Instructions
        instructions = ttk.Label(frame,
                                 text="Define rectangular regions that make up your floor plan. Each region has x, y coordinates, width, and height.",
                                 wraplength=800)
        instructions.pack(pady=(0, 10))

        # Regions list frame
        regions_frame = ttk.LabelFrame(frame, text="Regions", padding=10)
        regions_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Regions treeview
        columns = ("X", "Y", "Width", "Height")
        self.regions_tree = ttk.Treeview(regions_frame, columns=columns, show="tree headings", height=8)

        # Configure columns
        self.regions_tree.heading("#0", text="Region")
        self.regions_tree.column("#0", width=80)
        for col in columns:
            self.regions_tree.heading(col, text=col)
            self.regions_tree.column(col, width=80)

        self.regions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar for regions
        regions_scrollbar = ttk.Scrollbar(regions_frame, orient=tk.VERTICAL, command=self.regions_tree.yview)
        regions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.regions_tree.config(yscrollcommand=regions_scrollbar.set)

        # Region input frame
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=tk.X, pady=10)

        # Input fields
        ttk.Label(input_frame, text="X:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.region_x_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.region_x_var, width=10).grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Y:").grid(row=0, column=2, padx=5, sticky=tk.W)
        self.region_y_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.region_y_var, width=10).grid(row=0, column=3, padx=5)

        ttk.Label(input_frame, text="Width:").grid(row=0, column=4, padx=5, sticky=tk.W)
        self.region_width_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.region_width_var, width=10).grid(row=0, column=5, padx=5)

        ttk.Label(input_frame, text="Height:").grid(row=0, column=6, padx=5, sticky=tk.W)
        self.region_height_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.region_height_var, width=10).grid(row=0, column=7, padx=5)

        # Buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=0, column=8, padx=20)

        ttk.Button(button_frame, text="Add Region", command=self.add_region).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Edit Selected", command=self.edit_region).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_region).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Clear All", command=self.clear_regions).pack(side=tk.LEFT, padx=2)

    def init_rooms_screen(self):
        """Initialize the rooms screen with bulk addition functionality"""
        frame = ttk.Frame(self.content_frame)
        self.screens["rooms"] = frame

        # Title
        ttk.Label(frame, text="Room Specifications",
                  font=("Arial", 16, "bold")).pack(pady=(0, 20))

        # Instructions
        instructions = ttk.Label(frame,
                                 text="Define rooms with their dimensions and maximum expansion limits.",
                                 wraplength=800)
        instructions.pack(pady=(0, 10))

        # Rooms list frame
        rooms_frame = ttk.LabelFrame(frame, text="Rooms", padding=10)
        rooms_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Rooms treeview
        columns = ("Width", "Height", "Max Expansion")
        self.rooms_tree = ttk.Treeview(rooms_frame, columns=columns, show="tree headings", height=8)
        # Add this after creating the rooms_tree
        self.rooms_tree.bind("<Double-1>", lambda event: self.edit_room())
        # Configure columns
        self.rooms_tree.heading("#0", text="Room Name")
        self.rooms_tree.column("#0", width=120)
        for col in columns:
            self.rooms_tree.heading(col, text=col)
            self.rooms_tree.column(col, width=100)

        self.rooms_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar for rooms
        rooms_scrollbar = ttk.Scrollbar(rooms_frame, orient=tk.VERTICAL, command=self.rooms_tree.yview)
        rooms_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rooms_tree.config(yscrollcommand=rooms_scrollbar.set)

        # Single Room input frame
        single_input_frame = ttk.LabelFrame(frame, text="Add Single Room", padding=10)
        single_input_frame.pack(fill=tk.X, pady=5)

        # Input fields for single room
        ttk.Label(single_input_frame, text="Name:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.room_name_var = tk.StringVar()
        ttk.Entry(single_input_frame, textvariable=self.room_name_var, width=15).grid(row=0, column=1, padx=5)

        ttk.Label(single_input_frame, text="Width:").grid(row=0, column=2, padx=5, sticky=tk.W)
        self.room_width_var = tk.StringVar()
        ttk.Entry(single_input_frame, textvariable=self.room_width_var, width=10).grid(row=0, column=3, padx=5)

        ttk.Label(single_input_frame, text="Height:").grid(row=0, column=4, padx=5, sticky=tk.W)
        self.room_height_var = tk.StringVar()
        ttk.Entry(single_input_frame, textvariable=self.room_height_var, width=10).grid(row=0, column=5, padx=5)

        ttk.Label(single_input_frame, text="Max Expansion:").grid(row=0, column=6, padx=5, sticky=tk.W)
        self.room_max_exp_var = tk.StringVar()
        ttk.Entry(single_input_frame, textvariable=self.room_max_exp_var, width=10).grid(row=0, column=7, padx=5)

        # Single room button
        ttk.Button(single_input_frame, text="Add Room", command=self.add_room).grid(row=0, column=8, padx=10)

        # Bulk Room input frame
        bulk_input_frame = ttk.LabelFrame(frame, text="Add Multiple Rooms", padding=10)
        bulk_input_frame.pack(fill=tk.X, pady=5)

        # Input fields for bulk rooms
        ttk.Label(bulk_input_frame, text="Base Name:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.bulk_room_name_var = tk.StringVar()
        ttk.Entry(bulk_input_frame, textvariable=self.bulk_room_name_var, width=15).grid(row=0, column=1, padx=5)

        ttk.Label(bulk_input_frame, text="Quantity:").grid(row=0, column=2, padx=5, sticky=tk.W)
        self.bulk_room_quantity_var = tk.StringVar()
        ttk.Entry(bulk_input_frame, textvariable=self.bulk_room_quantity_var, width=10).grid(row=0, column=3, padx=5)

        ttk.Label(bulk_input_frame, text="Width:").grid(row=0, column=4, padx=5, sticky=tk.W)
        self.bulk_room_width_var = tk.StringVar()
        ttk.Entry(bulk_input_frame, textvariable=self.bulk_room_width_var, width=10).grid(row=0, column=5, padx=5)

        ttk.Label(bulk_input_frame, text="Height:").grid(row=0, column=6, padx=5, sticky=tk.W)
        self.bulk_room_height_var = tk.StringVar()
        ttk.Entry(bulk_input_frame, textvariable=self.bulk_room_height_var, width=10).grid(row=0, column=7, padx=5)

        ttk.Label(bulk_input_frame, text="Max Expansion:").grid(row=0, column=8, padx=5, sticky=tk.W)
        self.bulk_room_max_exp_var = tk.StringVar()
        ttk.Entry(bulk_input_frame, textvariable=self.bulk_room_max_exp_var, width=10).grid(row=0, column=9, padx=5)

        # Bulk room button
        ttk.Button(bulk_input_frame, text="Add Multiple Rooms", command=self.add_bulk_rooms).grid(row=0, column=10,
                                                                                                  padx=10)

        # Room management buttons frame
        management_frame = ttk.Frame(frame)
        management_frame.pack(fill=tk.X, pady=10)

        # Buttons
        ttk.Button(management_frame, text="Remove Selected", command=self.remove_room).pack(side=tk.LEFT, padx=5)
        ttk.Button(management_frame, text="Edit Selected", command=self.edit_room).pack(side=tk.LEFT, padx=5)
        ttk.Button(management_frame, text="Clear All", command=self.clear_rooms).pack(side=tk.LEFT, padx=5)

    def init_adjacency_screen(self):
        """Initialize the adjacency screen"""
        frame = ttk.Frame(self.content_frame)
        self.screens["adjacency"] = frame

        # Title
        ttk.Label(frame, text="Room Adjacency Requirements",
                  font=("Arial", 16, "bold")).pack(pady=(0, 20))

        # Instructions
        instructions = ttk.Label(frame,
                                 text="Define which rooms should be adjacent to each other (share a wall).",
                                 wraplength=800)
        instructions.pack(pady=(0, 10))

        # Main container
        main_container = ttk.Frame(frame)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Left side - Add adjacencies
        left_frame = ttk.LabelFrame(main_container, text="Add Adjacency", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Room selection
        ttk.Label(left_frame, text="Room 1:").pack(anchor=tk.W)
        self.room1_combo = ttk.Combobox(left_frame, state="readonly", width=20)
        self.room1_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(left_frame, text="Room 2:").pack(anchor=tk.W)
        self.room2_combo = ttk.Combobox(left_frame, state="readonly", width=20)
        self.room2_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(left_frame, text="Add Adjacency", command=self.add_adjacency).pack(pady=10)

        # Right side - Current adjacencies
        right_frame = ttk.LabelFrame(main_container, text="Current Adjacencies", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Adjacencies listbox
        self.adjacencies_listbox = tk.Listbox(right_frame, height=15)
        self.adjacencies_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar for adjacencies
        adj_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.adjacencies_listbox.yview)
        adj_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.adjacencies_listbox.config(yscrollcommand=adj_scrollbar.set)

        # Buttons for adjacencies
        adj_button_frame = ttk.Frame(right_frame)
        adj_button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(adj_button_frame, text="Remove Selected",
                   command=self.remove_adjacency).pack(side=tk.LEFT, padx=2)
        ttk.Button(adj_button_frame, text="Clear All",
                   command=self.clear_adjacencies).pack(side=tk.LEFT, padx=2)

    def init_non_adjacency_screen(self):
        """Initialize the non-adjacency screen"""
        frame = ttk.Frame(self.content_frame)
        self.screens["non_adjacency"] = frame

        # Title
        ttk.Label(frame, text="Room Non-Adjacency Requirements",
                  font=("Arial", 16, "bold")).pack(pady=(0, 20))

        # Instructions
        instructions = ttk.Label(frame,
                                 text="Define which rooms should NOT be adjacent to each other (should not share a wall).",
                                 wraplength=800)
        instructions.pack(pady=(0, 10))

        # Main container
        main_container = ttk.Frame(frame)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Left side - Add non-adjacencies
        left_frame = ttk.LabelFrame(main_container, text="Add Non-Adjacency", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Room selection
        ttk.Label(left_frame, text="Room 1:").pack(anchor=tk.W)
        self.non_adj_room1_combo = ttk.Combobox(left_frame, state="readonly", width=20)
        self.non_adj_room1_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(left_frame, text="Room 2:").pack(anchor=tk.W)
        self.non_adj_room2_combo = ttk.Combobox(left_frame, state="readonly", width=20)
        self.non_adj_room2_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(left_frame, text="Add Non-Adjacency", command=self.add_non_adjacency).pack(pady=10)

        # Right side - Current non-adjacencies
        right_frame = ttk.LabelFrame(main_container, text="Current Non-Adjacencies", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Non-adjacencies listbox
        self.non_adjacencies_listbox = tk.Listbox(right_frame, height=15)
        self.non_adjacencies_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar for non-adjacencies
        non_adj_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.non_adjacencies_listbox.yview)
        non_adj_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.non_adjacencies_listbox.config(yscrollcommand=non_adj_scrollbar.set)

        # Buttons for non-adjacencies
        non_adj_button_frame = ttk.Frame(right_frame)
        non_adj_button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(non_adj_button_frame, text="Remove Selected",
                   command=self.remove_non_adjacency).pack(side=tk.LEFT, padx=2)
        ttk.Button(non_adj_button_frame, text="Clear All",
                   command=self.clear_non_adjacencies).pack(side=tk.LEFT, padx=2)

    def get_non_adjacencies_data(self):
        """Get non-adjacencies data as list of dictionaries"""
        non_adjacencies = []
        for i in range(self.non_adjacencies_listbox.size()):
            non_adjacency_text = self.non_adjacencies_listbox.get(i)
            room1, room2 = non_adjacency_text.split(" ✗ ")
            non_adjacencies.append({"room1": room1, "room2": room2})
        return non_adjacencies

    def on_canvas_click(self, event):
        if event.xdata is None or event.ydata is None:
            return

        if self.add_mode.get() == "door":
            self.place_door(event.xdata, event.ydata)
            self.add_mode.set("none")
        elif self.add_mode.get() == "window":
            self.place_window(event.xdata, event.ydata)
            self.add_mode.set("none")

    def place_door(self, x, y):
        wall = None
        for room in self.floor_plan.rooms:
            if room.x is not None and room.y is not None:
                if abs(y - room.y) < 0.5 and room.x <= x <= room.x + room.width:
                    wall = "bottom"
                elif abs(y - (room.y + room.height)) < 0.5 and room.x <= x <= room.x + room.width:
                    wall = "top"
                elif abs(x - room.x) < 0.5 and room.y <= y <= room.y + room.height:
                    wall = "left"
                elif abs(x - (room.x + room.width)) < 0.5 and room.y <= y <= room.y + room.height:
                    wall = "right"
                if wall:
                    break

        if not wall:
            wall = "bottom"

        width = 0.9  # 3 feet door
        color = "brown"
        thickness = 3
        arc_color = "gray"

        if wall == "bottom":
            # door on bottom wall, opens upward
            self.ax.plot([x, x], [y, y + width], color=color, linewidth=thickness)  # vertical panel
            self.ax.plot([x, x + width], [y, y], color=color, linewidth=thickness)  # horizontal edge
            arc = mpatches.Arc((x, y), 2 * width, 2 * width, angle=0, theta1=0, theta2=90, color=arc_color, linewidth=2)

        elif wall == "top":
            self.ax.plot([x, x], [y, y - width], color=color, linewidth=thickness)
            self.ax.plot([x, x - width], [y, y], color=color, linewidth=thickness)
            arc = mpatches.Arc((x, y), 2 * width, 2 * width, angle=180, theta1=0, theta2=90, color=arc_color,
                               linewidth=2)

        elif wall == "left":
            self.ax.plot([x, x + width], [y, y], color=color, linewidth=thickness)
            self.ax.plot([x, x], [y, y - width], color=color, linewidth=thickness)
            arc = mpatches.Arc((x, y), 2 * width, 2 * width, angle=270, theta1=0, theta2=90, color=arc_color,
                               linewidth=2)

        elif wall == "right":
            self.ax.plot([x, x - width], [y, y], color=color, linewidth=thickness)
            self.ax.plot([x, x], [y, y + width], color=color, linewidth=thickness)
            arc = mpatches.Arc((x, y), 2 * width, 2 * width, angle=90, theta1=0, theta2=90, color=arc_color,
                               linewidth=2)

        self.ax.add_patch(arc)

        if not hasattr(self, 'placed_doors'):
            self.placed_doors = []
        self.placed_doors.append({"x": x, "y": y, "wall": wall})
        self.canvas.draw()

def place_window(self, x, y):
    wall = None
    for room in self.floor_plan.rooms:
        if room.x is not None and room.y is not None:
            if abs(y - room.y) < 0.5 and room.x <= x <= room.x + room.width:
                wall = "bottom"
            elif abs(y - (room.y + room.height)) < 0.5 and room.x <= x <= room.x + room.width:
                wall = "top"
            elif abs(x - room.x) < 0.5 and room.y <= y <= room.y + room.height:
                wall = "left"
            elif abs(x - (room.x + room.width)) < 0.5 and room.y <= y <= room.y + room.height:
                wall = "right"
            if wall:
                break

    if not wall:
        wall = "unknown"

    length = 0.9  # 3 feet
    half = length / 2
    color = "blue"
    thickness = 2.5      # ⬅️ reduced main thickness
    cap_thickness = 1.5  # ⬅️ reduced cap thickness
    spacing = 0.1

    if wall in ["top", "bottom"]:
        self.ax.plot([x - half, x + half], [y + spacing, y + spacing], color=color, linewidth=thickness)
        self.ax.plot([x - half, x + half], [y - spacing, y - spacing], color=color, linewidth=thickness)
        self.ax.plot([x - half, x - half], [y - spacing, y + spacing], color=color, linewidth=cap_thickness)
        self.ax.plot([x + half, x + half], [y - spacing, y + spacing], color=color, linewidth=cap_thickness)

    elif wall in ["left", "right"]:
        self.ax.plot([x + spacing, x + spacing], [y - half, y + half], color=color, linewidth=thickness)
        self.ax.plot([x - spacing, x - spacing], [y - half, y + half], color=color, linewidth=thickness)
        self.ax.plot([x - spacing, x + spacing], [y - half, y - half], color=color, linewidth=cap_thickness)
        self.ax.plot([x - spacing, x + spacing], [y + half, y + half], color=color, linewidth=cap_thickness)

    if not hasattr(self, 'placed_windows'):
        self.placed_windows = []
    self.placed_windows.append({"x": x, "y": y, "wall": wall})
    self.canvas.draw()

    def init_output_screen(self):
        """Initialize the output screen"""
        frame = ttk.Frame(self.content_frame)
        self.screens["output"] = frame
        self.add_mode = tk.StringVar(value="none")

        # Title
        ttk.Label(frame, text="Floor Plan Output",
                  font=("Arial", 16, "bold")).pack(pady=(0, 20))

        # Create paned window for split view
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left side - Statistics and controls
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=1)

        # Controls frame
        controls_frame = ttk.LabelFrame(left_panel, text="Generation Controls", padding=10)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        # First row - generation controls
        gen_controls_row = ttk.Frame(controls_frame)
        gen_controls_row.pack(fill=tk.X, pady=(0, 10))

        # Add Door/Window buttons
        ttk.Button(gen_controls_row, text="Add Door", command=lambda: self.add_mode.set("door")).grid(row=0, column=4,
                                                                                                      padx=5)

        ttk.Button(gen_controls_row, text="Add Window", command=lambda: self.add_mode.set("window")).grid(row=0,
                                                                                                          column=5,
                                                                                                          padx=5)

        # Max attempts
        ttk.Label(gen_controls_row, text="Max Attempts:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.max_attempts_var = tk.StringVar(value="1000")
        ttk.Entry(gen_controls_row, textvariable=self.max_attempts_var, width=10).grid(row=0, column=1, padx=5)

        # Enable expansion
        self.enable_expansion_var = tk.BooleanVar(value=True)
        self.enable_space_optimization_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(gen_controls_row, text="Enable Room Expansion",
                        variable=self.enable_expansion_var).grid(row=0, column=2, padx=20)
        ttk.Checkbutton(gen_controls_row, text="Enable Space Optimization",
                        variable=self.enable_space_optimization_var).grid(row=0, column=3, padx=20)

        # Second row - save controls
        save_controls_row = ttk.Frame(controls_frame)
        save_controls_row.pack(fill=tk.X)

        ttk.Button(save_controls_row, text="Save as JSON",
                   command=self.save_floor_plan_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_controls_row, text="Load from JSON",
                   command=self.load_floor_plan_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(gen_controls_row, text="Add Door", command=lambda: self.add_mode.set("door")).grid(row=0, column=4,
                                                                                                      padx=5)
        ttk.Button(gen_controls_row, text="Add Window", command=lambda: self.add_mode.set("window")).grid(row=0,
                                                                                                          column=5,
                                                                                                          padx=5)

        # Statistics frame
        stats_frame = ttk.LabelFrame(left_panel, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True)

        # Statistics text
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=20, width=40)
        self.stats_text.pack(fill=tk.BOTH, expand=True)

        # Right side - Visualization
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=2)

        # Visualization frame
        viz_frame = ttk.LabelFrame(right_panel, text="Floor Plan Visualization", padding=10)
        viz_frame.pack(fill=tk.BOTH, expand=True)

        # Matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, viz_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect("button_press_event", self.on_canvas_click)

    def save_floor_plan_json(self):
        """Save the current floor plan configuration and results to JSON"""
        try:
            # Get file path from user
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Save Floor Plan"
            )

            if not file_path:
                return  # User cancelled

            # Collect all data
            data = {
                "metadata": {
                    "version": "1.0",
                    "created_at": self.get_current_timestamp(),
                    "description": "Floor plan configuration and results"
                },
                "regions": self.get_regions_data(),
                "rooms": self.get_rooms_data(),
                "adjacencies": self.get_adjacencies_data(),
                "generation_settings": {
                    "max_attempts": int(self.max_attempts_var.get()),
                    "enable_expansion": self.enable_expansion_var.get()
                }
            }

            # Add floor plan results if generated
            if self.floor_plan:
                data["results"] = self.get_floor_plan_results()

            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Success", f"Floor plan saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save floor plan:\n{str(e)}")

    def load_floor_plan_json(self):
        """Load floor plan configuration from JSON and automatically generate if results exist"""
        try:
            # Get file path from user
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Load Floor Plan"
            )

            if not file_path:
                return  # User cancelled

            # Load from file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Clear existing data
            self.clear_all_data()

            # Load regions
            if "regions" in data:
                for i, region in enumerate(data["regions"]):
                    item = self.regions_tree.insert("", "end", text=f"Region {i + 1}")
                    self.regions_tree.set(item, "X", region['x'])
                    self.regions_tree.set(item, "Y", region['y'])
                    self.regions_tree.set(item, "Width", region['width'])
                    self.regions_tree.set(item, "Height", region['height'])

            # Load rooms
            if "rooms" in data:
                for room in data["rooms"]:
                    item = self.rooms_tree.insert("", "end", text=room['name'])
                    self.rooms_tree.set(item, "Width", room['width'])
                    self.rooms_tree.set(item, "Height", room['height'])
                    self.rooms_tree.set(item, "Max Expansion", room['max_expansion'])

            # Load adjacencies
            if "adjacencies" in data:
                for adj in data["adjacencies"]:
                    self.adjacencies_listbox.insert(tk.END, f"{adj['room1']} ↔ {adj['room2']}")

            # Load generation settings
            if "generation_settings" in data:
                settings = data["generation_settings"]
                self.max_attempts_var.set(str(settings.get("max_attempts", 1000)))
                self.enable_expansion_var.set(settings.get("enable_expansion", True))

            # Check if the loaded JSON has results and ask user if they want to restore them
            has_results = "results" in data and data["results"] is not None

            if has_results:
                response = messagebox.askyesno(
                    "Restore Results",
                    "This file contains previous floor plan results.\n\n"
                    "Do you want to:\n"
                    "• YES: Restore the exact previous layout\n"
                    "• NO: Generate a new layout with current settings"
                )

                if response:  # User chose YES - restore exact layout
                    self.restore_floor_plan_from_results(data["results"])
                    messagebox.showinfo("Success", f"Floor plan and results restored from:\n{file_path}")
                else:  # User chose NO - generate new layout
                    self.generate_floor_plan()
                    messagebox.showinfo("Success",
                                        f"Floor plan configuration loaded from:\n{file_path}\nNew layout generated.")
            else:
                # No results in file, ask if user wants to generate now
                response = messagebox.askyesno(
                    "Generate Floor Plan",
                    "Floor plan configuration loaded successfully.\n\n"
                    "Do you want to generate the floor plan now?"
                )

                if response:
                    self.generate_floor_plan()
                    messagebox.showinfo("Success", f"Floor plan loaded and generated from:\n{file_path}")
                else:
                    messagebox.showinfo("Success", f"Floor plan configuration loaded from:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load floor plan:\n{str(e)}")

    def restore_floor_plan_from_results(self, results_data):
        """Restore floor plan from saved results data"""
        try:
            # Create floor plan with current regions
            regions = self.get_regions_data()
            if not regions:
                raise ValueError("No regions defined")

            self.floor_plan = FloorPlan(regions)

            # Add rooms with original specifications
            room_names = []
            for item in self.rooms_tree.get_children():
                name = self.rooms_tree.item(item)['text']
                width = int(self.rooms_tree.set(item, "Width"))
                height = int(self.rooms_tree.set(item, "Height"))
                max_exp = int(self.rooms_tree.set(item, "Max Expansion"))

                self.floor_plan.add_room(name, width, height, max_exp)
                room_names.append(name)

            # Add adjacencies
            for i in range(self.adjacencies_listbox.size()):
                adjacency = self.adjacencies_listbox.get(i)
                room1, room2 = adjacency.split(" ↔ ")
                self.floor_plan.add_adjacency(room1, room2)

            # Restore room placements from saved results
            if "room_placements" in results_data:
                for placement in results_data["room_placements"]:
                    # Find the room object
                    room = next((r for r in self.floor_plan.rooms if r.name == placement["name"]), None)
                    if room:
                        # Restore the placement
                        room.x = placement["x"]
                        room.y = placement["y"]
                        room.width = placement["width"]
                        room.height = placement["height"]
                        room.rotated = placement.get("rotated", False)

                        # Ensure original dimensions are preserved
                        if not hasattr(room, 'original_width'):
                            room.original_width = placement.get("original_width", placement["width"])
                            room.original_height = placement.get("original_height", placement["height"])

            # Update the display
            self.update_output_display()

        except Exception as e:
            # If restoration fails, fall back to generating new layout
            messagebox.showwarning("Restoration Failed",
                                   f"Could not restore exact layout: {str(e)}\n"
                                   "Generating new layout instead...")
            self.generate_floor_plan()

    def get_regions_data(self):
        """Get regions data as list of dictionaries"""
        regions = []
        for item in self.regions_tree.get_children():
            region = {
                "x": int(self.regions_tree.set(item, "X")),
                "y": int(self.regions_tree.set(item, "Y")),
                "width": int(self.regions_tree.set(item, "Width")),
                "height": int(self.regions_tree.set(item, "Height"))
            }
            regions.append(region)
        return regions

    def get_rooms_data(self):
        """Get rooms data as list of dictionaries"""
        rooms = []
        for item in self.rooms_tree.get_children():
            room = {
                "name": self.rooms_tree.item(item)['text'],
                "width": int(self.rooms_tree.set(item, "Width")),
                "height": int(self.rooms_tree.set(item, "Height")),
                "max_expansion": int(self.rooms_tree.set(item, "Max Expansion"))
            }
            rooms.append(room)
        return rooms

    def get_adjacencies_data(self):
        """Get adjacencies data as list of dictionaries"""
        adjacencies = []
        for i in range(self.adjacencies_listbox.size()):
            adjacency_text = self.adjacencies_listbox.get(i)
            room1, room2 = adjacency_text.split(" ↔ ")
            adjacencies.append({"room1": room1, "room2": room2})
        return adjacencies

    def get_floor_plan_results(self):
        """Get floor plan generation results"""
        if not self.floor_plan:
            return None

        # Calculate statistics
        total_area = sum(region['width'] * region['height'] for region in self.floor_plan.floor_regions)
        used_area = sum(room.width * room.height for room in self.floor_plan.rooms if room.x is not None)
        score, adjacent_pairs, violations = self.floor_plan.evaluate_adjacency_score()

        # Get room placements
        room_placements = []
        for room in self.floor_plan.rooms:
            if room.x is not None:
                placement = {
                    "name": room.name,
                    "x": room.x,
                    "y": room.y,
                    "width": room.width,
                    "height": room.height,
                    "original_width": room.original_width,
                    "original_height": room.original_height,
                    "rotated": room.rotated,
                    "max_expansion": room.max_expansion
                }
                room_placements.append(placement)

        return {
            "statistics": {
                "total_floor_area": total_area,
                "used_area": used_area,
                "space_utilization": used_area / total_area if total_area > 0 else 0,
                "adjacency_score": score,
                "total_adjacency_requirements": len(self.floor_plan.adjacency_graph.edges),
                "satisfied_adjacencies": len(adjacent_pairs)
            },
            "room_placements": room_placements,
            "satisfied_adjacencies": [{"room1": pair[0], "room2": pair[1]} for pair in adjacent_pairs]
        }

    def get_current_timestamp(self):
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def show_screen(self, screen_name):
        """Show the specified screen and hide others"""
        # Hide all screens
        for screen in self.screens.values():
            screen.pack_forget()

        # Show selected screen
        if screen_name in self.screens:
            self.screens[screen_name].pack(fill=tk.BOTH, expand=True)
            self.current_screen = screen_name

            # Update button states (optional visual feedback)
            for name, btn in self.nav_buttons.items():
                if name == screen_name:
                    btn.state(['pressed'])
                else:
                    btn.state(['!pressed'])

            # Refresh data if switching to certain screens
            if screen_name == "adjacency":
                self.refresh_room_combos()
            elif screen_name == "non_adjacency":
                self.refresh_non_adjacency_combos()

    def refresh_non_adjacency_combos(self):
        """Refresh the non-adjacency room combo boxes with current room names"""
        room_names = [self.rooms_tree.item(item)['text'] for item in self.rooms_tree.get_children()]
        self.non_adj_room1_combo['values'] = room_names
        self.non_adj_room2_combo['values'] = room_names

    def add_non_adjacency(self):
        """Add a new non-adjacency"""
        room1 = self.non_adj_room1_combo.get()
        room2 = self.non_adj_room2_combo.get()

        if not room1 or not room2:
            messagebox.showerror("Error", "Please select both rooms")
            return

        if room1 == room2:
            messagebox.showerror("Error", "A room cannot be non-adjacent to itself")
            return

        # Check if non-adjacency already exists (in either direction)
        non_adjacency1 = f"{room1} ✗ {room2}"
        non_adjacency2 = f"{room2} ✗ {room1}"

        for i in range(self.non_adjacencies_listbox.size()):
            existing = self.non_adjacencies_listbox.get(i)
            if existing == non_adjacency1 or existing == non_adjacency2:
                messagebox.showerror("Error", "This non-adjacency already exists")
                return

        # Add non-adjacency
        self.non_adjacencies_listbox.insert(tk.END, non_adjacency1)

        # Clear selections
        self.non_adj_room1_combo.set("")
        self.non_adj_room2_combo.set("")

    def remove_non_adjacency(self):
        """Remove selected non-adjacency"""
        selection = self.non_adjacencies_listbox.curselection()
        if selection:
            self.non_adjacencies_listbox.delete(selection[0])

    def clear_non_adjacencies(self):
        """Clear all non-adjacencies"""
        self.non_adjacencies_listbox.delete(0, tk.END)

    def load_example_data(self):
        """Load the example data from the original code"""
        # Clear existing data
        self.clear_all_data()

        # Load example regions
        example_regions = [
            {'x': 0, 'y': 0, 'width': 10, 'height': 10},
            {'x': 10, 'y': 0, 'width': 8, 'height': 5},
            {'x': 0, 'y': 10, 'width': 5, 'height': 8},
            {'x': 10, 'y': 5, 'width': 6, 'height': 6}
        ]

        for i, region in enumerate(example_regions):
            item = self.regions_tree.insert("", "end", text=f"Region {i + 1}")
            self.regions_tree.set(item, "X", region['x'])
            self.regions_tree.set(item, "Y", region['y'])
            self.regions_tree.set(item, "Width", region['width'])
            self.regions_tree.set(item, "Height", region['height'])

        # Load example rooms
        example_rooms = [
            ("Living Room", 8, 4, 15),
            ("Kitchen", 6, 4, 8),
            ("Bedroom 1", 5, 4, 10),
            ("Bedroom 2", 5, 4, 6),
            ("Bathroom", 3, 4, 2),
            ("Hallway", 2, 4, 5),
            ("Office", 3, 3, 0),
            ("secretRoom", 3, 3, 3)
        ]

        for room_data in example_rooms:
            name, width, height, max_exp = room_data
            item = self.rooms_tree.insert("", "end", text=name)
            self.rooms_tree.set(item, "Width", width)
            self.rooms_tree.set(item, "Height", height)
            self.rooms_tree.set(item, "Max Expansion", max_exp)

        # Load example adjacencies
        example_adjacencies = [
            ("Living Room", "Kitchen"),
            ("Living Room", "Bathroom"),
            ("Kitchen", "Bedroom 1"),
            ("Bedroom 2", "Hallway"),
            ("Hallway", "Bathroom"),
            ("Office", "Bedroom 2"),
            ("secretRoom", "Kitchen")
        ]

        for room1, room2 in example_adjacencies:
            self.adjacencies_listbox.insert(tk.END, f"{room1} ↔ {room2}")

    def clear_all_data(self):
        """Clear all data from the GUI"""
        # Clear regions
        for item in self.regions_tree.get_children():
            self.regions_tree.delete(item)

        # Clear rooms
        for item in self.rooms_tree.get_children():
            self.rooms_tree.delete(item)

        # Clear adjacencies
        self.adjacencies_listbox.delete(0, tk.END)

    def add_region(self):
        """Add a new region"""
        try:
            x = int(self.region_x_var.get())
            y = int(self.region_y_var.get())
            width = int(self.region_width_var.get())
            height = int(self.region_height_var.get())

            if width <= 0 or height <= 0:
                messagebox.showerror("Error", "Width and height must be positive")
                return

            # Add to tree
            region_count = len(self.regions_tree.get_children()) + 1
            item = self.regions_tree.insert("", "end", text=f"Region {region_count}")
            self.regions_tree.set(item, "X", x)
            self.regions_tree.set(item, "Y", y)
            self.regions_tree.set(item, "Width", width)
            self.regions_tree.set(item, "Height", height)

            # Clear input fields
            self.region_x_var.set("")
            self.region_y_var.set("")
            self.region_width_var.set("")
            self.region_height_var.set("")

        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    def remove_region(self):
        """Remove selected region"""
        selected = self.regions_tree.selection()
        if selected:
            self.regions_tree.delete(selected[0])

    def edit_region(self):
        """Edit the selected region"""
        selected = self.regions_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a region to edit")
            return

        # Get current values from the selected region
        item = selected[0]
        current_x = self.regions_tree.set(item, "X")
        current_y = self.regions_tree.set(item, "Y")
        current_width = self.regions_tree.set(item, "Width")
        current_height = self.regions_tree.set(item, "Height")

        # Populate input fields with current values
        self.region_x_var.set(current_x)
        self.region_y_var.set(current_y)
        self.region_width_var.set(current_width)
        self.region_height_var.set(current_height)

        # Remove the selected region (it will be re-added with new values when user clicks Add)
        region_name = self.regions_tree.item(item)['text']
        self.regions_tree.delete(item)

        # Show message to user
        messagebox.showinfo("Edit Mode",
                            f"Region values loaded into input fields.\nModify the values and click 'Add Region' to save changes.\n\nNote: {region_name} has been temporarily removed.")

    def clear_regions(self):
        """Clear all regions"""
        for item in self.regions_tree.get_children():
            self.regions_tree.delete(item)

    def edit_room(self):
        """Edit the selected room"""
        selected = self.rooms_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a room to edit")
            return

        # Store edit context for the dialog
        self.edit_context = {
            'selected_item': selected[0],
            'current_name': self.rooms_tree.item(selected[0])['text'],
            'current_width': self.rooms_tree.set(selected[0], "Width"),
            'current_height': self.rooms_tree.set(selected[0], "Height"),
            'current_max_exp': self.rooms_tree.set(selected[0], "Max Expansion")
        }

        # Create edit dialog
        self.edit_window = tk.Toplevel(self.root)
        self.edit_window.title("Edit Room")
        self.edit_window.geometry("400x300")  # Increased height
        self.edit_window.resizable(False, False)
        self.edit_window.transient(self.root)
        self.edit_window.grab_set()

        # Center the dialog
        self.edit_window.update_idletasks()
        x = (self.edit_window.winfo_screenwidth() // 2) - (self.edit_window.winfo_width() // 2)
        y = (self.edit_window.winfo_screenheight() // 2) - (self.edit_window.winfo_height() // 2)
        self.edit_window.geometry(f"+{x}+{y}")

        # Create form
        main_frame = ttk.Frame(self.edit_window, padding=15)  # Reduced padding
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Edit Room Properties",
                  font=("Arial", 12, "bold")).pack(pady=(0, 10))  # Reduced padding

        # Form fields
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.X, pady=5)  # Reduced padding

        # Name field
        ttk.Label(fields_frame, text="Room Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.edit_name_var = tk.StringVar(value=self.edit_context['current_name'])
        name_entry = ttk.Entry(fields_frame, textvariable=self.edit_name_var, width=20)
        name_entry.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.W)

        # Width field
        ttk.Label(fields_frame, text="Width:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.edit_width_var = tk.StringVar(value=self.edit_context['current_width'])
        width_entry = ttk.Entry(fields_frame, textvariable=self.edit_width_var, width=20)
        width_entry.grid(row=1, column=1, padx=(10, 0), pady=5, sticky=tk.W)

        # Height field
        ttk.Label(fields_frame, text="Height:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.edit_height_var = tk.StringVar(value=self.edit_context['current_height'])
        height_entry = ttk.Entry(fields_frame, textvariable=self.edit_height_var, width=20)
        height_entry.grid(row=2, column=1, padx=(10, 0), pady=5, sticky=tk.W)

        # Max Expansion field
        ttk.Label(fields_frame, text="Max Expansion:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.edit_max_exp_var = tk.StringVar(value=self.edit_context['current_max_exp'])
        max_exp_entry = ttk.Entry(fields_frame, textvariable=self.edit_max_exp_var, width=20)
        max_exp_entry.grid(row=3, column=1, padx=(10, 0), pady=5, sticky=tk.W)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 10))  # Reduced padding

        ttk.Button(button_frame, text="Save Changes",
                   command=self.save_room_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel",
                   command=self.cancel_room_edit).pack(side=tk.LEFT, padx=5)

        # Focus on name field and select all text
        name_entry.focus()
        name_entry.select_range(0, tk.END)

    def add_bulk_rooms(self):
        """Add multiple rooms with sequential naming"""
        try:
            base_name = self.bulk_room_name_var.get().strip()
            quantity = int(self.bulk_room_quantity_var.get())
            width = int(self.bulk_room_width_var.get())
            height = int(self.bulk_room_height_var.get())
            max_exp = int(self.bulk_room_max_exp_var.get())

            # Validation
            if not base_name:
                messagebox.showerror("Error", "Please enter a base room name")
                return

            if quantity <= 0:
                messagebox.showerror("Error", "Quantity must be positive")
                return

            if width <= 0 or height <= 0:
                messagebox.showerror("Error", "Width and height must be positive")
                return

            if max_exp < 0:
                messagebox.showerror("Error", "Max expansion cannot be negative")
                return

            # Get existing room names to check for conflicts
            existing_names = {self.rooms_tree.item(item)['text'] for item in self.rooms_tree.get_children()}

            # Generate room names and check for conflicts
            new_room_names = []
            for i in range(1, quantity + 1):
                room_name = f"{base_name}{i}"
                if room_name in existing_names:
                    messagebox.showerror("Error", f"Room name '{room_name}' already exists")
                    return
                new_room_names.append(room_name)

            # Add all rooms
            added_count = 0
            for room_name in new_room_names:
                try:
                    # Add to tree
                    item = self.rooms_tree.insert("", "end", text=room_name)
                    self.rooms_tree.set(item, "Width", width)
                    self.rooms_tree.set(item, "Height", height)
                    self.rooms_tree.set(item, "Max Expansion", max_exp)
                    added_count += 1
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add room '{room_name}': {str(e)}")
                    break

            if added_count > 0:
                # Clear input fields
                self.bulk_room_name_var.set("")
                self.bulk_room_quantity_var.set("")
                self.bulk_room_width_var.set("")
                self.bulk_room_height_var.set("")
                self.bulk_room_max_exp_var.set("")

                # Refresh room combos
                self.refresh_room_combos()

                messagebox.showinfo("Success", f"Successfully added {added_count} rooms")

        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    def save_room_changes(self):
        """Save the edited room data"""
        try:
            new_name = self.edit_name_var.get().strip()
            new_width = int(self.edit_width_var.get())
            new_height = int(self.edit_height_var.get())
            new_max_exp = int(self.edit_max_exp_var.get())

            # Validation
            if not new_name:
                messagebox.showerror("Error", "Please enter a room name")
                return

            if new_width <= 0 or new_height <= 0:
                messagebox.showerror("Error", "Width and height must be positive")
                return

            if new_max_exp < 0:
                messagebox.showerror("Error", "Max expansion cannot be negative")
                return

            # Check if new name already exists (but allow keeping the same name)
            current_name = self.edit_context['current_name']
            if new_name != current_name:
                for item in self.rooms_tree.get_children():
                    if self.rooms_tree.item(item)['text'] == new_name:
                        messagebox.showerror("Error", "Room name already exists")
                        return

            # Update adjacencies if room name changed
            if new_name != current_name:
                self.update_adjacencies_after_room_rename(current_name, new_name)

            # Update the treeview item
            selected_item = self.edit_context['selected_item']
            self.rooms_tree.item(selected_item, text=new_name)
            self.rooms_tree.set(selected_item, "Width", new_width)
            self.rooms_tree.set(selected_item, "Height", new_height)
            self.rooms_tree.set(selected_item, "Max Expansion", new_max_exp)

            # Refresh room combos if name changed
            if new_name != current_name:
                self.refresh_room_combos()

            self.edit_window.destroy()
            messagebox.showinfo("Success", "Room updated successfully")

        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    def cancel_room_edit(self):
        """Cancel editing"""
        self.edit_window.destroy()

    def update_adjacencies_after_room_rename(self, old_name, new_name):
        """Update adjacency list when a room is renamed"""
        # Get all adjacencies
        adjacencies = []
        for i in range(self.adjacencies_listbox.size()):
            adjacency = self.adjacencies_listbox.get(i)
            # Replace old room name with new name in adjacency strings
            if old_name in adjacency:
                updated_adjacency = adjacency.replace(old_name, new_name)
                adjacencies.append(updated_adjacency)
            else:
                adjacencies.append(adjacency)

        # Clear and repopulate the listbox
        self.adjacencies_listbox.delete(0, tk.END)
        for adjacency in adjacencies:
            self.adjacencies_listbox.insert(tk.END, adjacency)

    def add_room(self):
        """Add a new room"""
        try:
            name = self.room_name_var.get().strip()
            width = int(self.room_width_var.get())
            height = int(self.room_height_var.get())
            max_exp = int(self.room_max_exp_var.get())

            if not name:
                messagebox.showerror("Error", "Please enter a room name")
                return

            if width <= 0 or height <= 0:
                messagebox.showerror("Error", "Width and height must be positive")
                return

            if max_exp < 0:
                messagebox.showerror("Error", "Max expansion cannot be negative")
                return

            # Check if room name already exists
            for item in self.rooms_tree.get_children():
                if self.rooms_tree.item(item)['text'] == name:
                    messagebox.showerror("Error", "Room name already exists")
                    return

            # Add to tree
            item = self.rooms_tree.insert("", "end", text=name)
            self.rooms_tree.set(item, "Width", width)
            self.rooms_tree.set(item, "Height", height)
            self.rooms_tree.set(item, "Max Expansion", max_exp)

            # Clear input fields
            self.room_name_var.set("")
            self.room_width_var.set("")
            self.room_height_var.set("")
            self.room_max_exp_var.set("")

        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    def remove_room(self):
        """Remove selected room"""
        selected = self.rooms_tree.selection()
        if selected:
            room_name = self.rooms_tree.item(selected[0])['text']
            self.rooms_tree.delete(selected[0])

            # Remove any adjacencies involving this room
            items_to_remove = []
            for i in range(self.adjacencies_listbox.size()):
                adjacency = self.adjacencies_listbox.get(i)
                if room_name in adjacency:
                    items_to_remove.append(i)

            # Remove from bottom to top to maintain indices
            for i in reversed(items_to_remove):
                self.adjacencies_listbox.delete(i)

    def clear_rooms(self):
        """Clear all rooms"""
        for item in self.rooms_tree.get_children():
            self.rooms_tree.delete(item)
        self.adjacencies_listbox.delete(0, tk.END)  # Clear adjacencies too

    def refresh_room_combos(self):
        """Refresh the room combo boxes with current room names"""
        room_names = [self.rooms_tree.item(item)['text'] for item in self.rooms_tree.get_children()]
        self.room1_combo['values'] = room_names
        self.room2_combo['values'] = room_names

    def add_adjacency(self):
        """Add a new adjacency"""
        room1 = self.room1_combo.get()
        room2 = self.room2_combo.get()

        if not room1 or not room2:
            messagebox.showerror("Error", "Please select both rooms")
            return

        if room1 == room2:
            messagebox.showerror("Error", "A room cannot be adjacent to itself")
            return

        # Check if adjacency already exists (in either direction)
        adjacency1 = f"{room1} ↔ {room2}"
        adjacency2 = f"{room2} ↔ {room1}"

        for i in range(self.adjacencies_listbox.size()):
            existing = self.adjacencies_listbox.get(i)
            if existing == adjacency1 or existing == adjacency2:
                messagebox.showerror("Error", "This adjacency already exists")
                return

        # Add adjacency
        self.adjacencies_listbox.insert(tk.END, adjacency1)

        # Clear selections
        self.room1_combo.set("")
        self.room2_combo.set("")

    def remove_adjacency(self):
        """Remove selected adjacency"""
        selection = self.adjacencies_listbox.curselection()
        if selection:
            self.adjacencies_listbox.delete(selection[0])

    def clear_adjacencies(self):
        """Clear all adjacencies"""
        self.adjacencies_listbox.delete(0, tk.END)

    def generate_floor_plan(self):
        """Generate the floor plan based on current data"""
        try:
            # Collect regions
            regions = []
            for item in self.regions_tree.get_children():
                x = int(self.regions_tree.set(item, "X"))
                y = int(self.regions_tree.set(item, "Y"))
                width = int(self.regions_tree.set(item, "Width"))
                height = int(self.regions_tree.set(item, "Height"))
                regions.append({'x': x, 'y': y, 'width': width, 'height': height})

            if not regions:
                messagebox.showerror("Error", "Please define at least one region")
                return

            # Create floor plan
            self.floor_plan = FloorPlan(regions)

            # Add rooms
            room_names = []
            for item in self.rooms_tree.get_children():
                name = self.rooms_tree.item(item)['text']
                width = int(self.rooms_tree.set(item, "Width"))
                height = int(self.rooms_tree.set(item, "Height"))
                max_exp = int(self.rooms_tree.set(item, "Max Expansion"))

                self.floor_plan.add_room(name, width, height, max_exp)
                room_names.append(name)

            if not room_names:
                messagebox.showerror("Error", "Please define at least one room")
                return

            # Add adjacencies
            for i in range(self.adjacencies_listbox.size()):
                adjacency = self.adjacencies_listbox.get(i)
                room1, room2 = adjacency.split(" ↔ ")
                self.floor_plan.add_adjacency(room1, room2)

            # Add non-adjacencies
            for i in range(self.non_adjacencies_listbox.size()):
                non_adjacency = self.non_adjacencies_listbox.get(i)
                room1, room2 = non_adjacency.split(" ✗ ")
                self.floor_plan.add_non_adjacency(room1, room2)
                print(f"Added non-adjacency: {room1} ✗ {room2}")

            print(f"Total non-adjacencies added: {self.non_adjacencies_listbox.size()}")

            # Generate floor plan
            max_attempts = int(self.max_attempts_var.get())
            enable_expansion = self.enable_expansion_var.get()

            success = self.floor_plan.place_rooms_with_constraints_optimized(
                use_compact_mode=self.enable_space_optimization_var.get(),
                max_attempts=max_attempts,
                enable_expansion=enable_expansion
            )

            if success:
                self.floor_plan.compact_rooms()
                self.floor_plan.enforce_minimum_adjacency()
                self.floor_plan.compact_rooms()

                messagebox.showinfo("Success", "Floor plan generated successfully!")
                self.update_output_display()
            else:
                messagebox.showwarning("Warning",
                                       "Failed to place all rooms optimally. You may need to adjust room sizes or floor dimensions.")
                self.update_output_display()

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            import traceback
            traceback.print_exc()

    def update_output_display(self):
        """Update the output display with statistics and visualization"""
        if not self.floor_plan:
            return

        # Update statistics
        self.stats_text.delete('1.0', tk.END)

        # Calculate and display statistics
        total_area = sum(region['width'] * region['height'] for region in self.floor_plan.floor_regions)
        used_area = sum(room.width * room.height for room in self.floor_plan.rooms if room.x is not None)

        stats = f"FLOOR PLAN STATISTICS\n{'=' * 30}\n\n"
        stats += f"Floor area: {total_area} square units\n"
        stats += f"Room area: {used_area} square units\n"
        stats += f"Space utilization: {used_area / total_area:.2%}\n\n"

        score, adjacent_pairs, violations = self.floor_plan.evaluate_adjacency_score()
        stats += f"Adjacency score: {score}/{len(self.floor_plan.adjacency_graph.edges)}\n"
        stats += f"Adjacent pairs: {adjacent_pairs}\n\n"

        stats += "ROOM EXPANSION STATISTICS:\n" + "-" * 30 + "\n"
        for room in self.floor_plan.rooms:
            if room.x is not None:
                original_area = room.original_width * room.original_height
                current_area = room.width * room.height
                expansion_pct = (current_area - original_area) / original_area * 100 if original_area > 0 else 0

                if not room.rotated:
                    total_expansion = (room.width - room.original_width) + (room.height - room.original_height)
                else:
                    total_expansion = (room.width - room.original_height) + (room.height - room.original_width)

                expansion_usage = f"{total_expansion}/{room.max_expansion}"

                stats += f"{room.name}: {room.original_width}x{room.original_height} → {room.width}x{room.height} "
                stats += f"({expansion_pct:.1f}% increase, expansion used: {expansion_usage})\n"

        stats += "\nROOM PLACEMENTS:\n" + "-" * 20 + "\n"
        for room in self.floor_plan.rooms:
            stats += f"{room}\n"

        self.stats_text.insert('1.0', stats)

        # Update visualization
        self.ax.clear()
        self.visualize_floor_plan()
        self.canvas.draw()

        # Switch to output screen
        self.show_screen("output")

    def visualize_floor_plan(self):
        """Create matplotlib visualization of the floor plan optimized for large numbers of rooms"""
        if not self.floor_plan:
            return

        # Clear the axis
        self.ax.clear()

        # Calculate dynamic sizing based on number of rooms and floor dimensions
        num_rooms = len(self.floor_plan.rooms)
        floor_area = self.floor_plan.floor_width * self.floor_plan.floor_height
        avg_room_area = floor_area / max(num_rooms, 1)

        # Dynamic font sizing based on room count and average room size
        base_font_size = max(4, min(12, int(np.sqrt(avg_room_area) / 3)))
        title_font_size = max(8, min(16, base_font_size + 4))

        # Draw floor shape with reduced opacity for large plans
        floor_alpha = max(0.1, min(0.3, 1.0 / np.sqrt(num_rooms / 10 + 1)))
        for region in self.floor_plan.floor_regions:
            rect = Rectangle(
                (region['x'], region['y']),
                region['width'],
                region['height'],
                linewidth=max(0.5, min(2, 10 / np.sqrt(num_rooms))),
                edgecolor='black',
                facecolor='lightgray',
                alpha=floor_alpha,
                linestyle='--'
            )
            self.ax.add_patch(rect)

        # Use a more distinguishable color palette for many rooms
        if num_rooms <= 20:
            colors = plt.cm.tab20(np.linspace(0, 1, num_rooms))
        else:
            # For large numbers, use HSV color space for better distribution
            colors = plt.cm.hsv(np.linspace(0, 1, num_rooms))

        # Calculate constraint violations efficiently
        room_violations = self._calculate_room_violations()

        # Determine room styling based on count
        show_room_details = num_rooms <= 50
        show_expansion_info = num_rooms <= 30
        room_line_width = max(0.3, min(2, 20 / np.sqrt(num_rooms)))
        violation_line_width = max(0.5, min(3, 30 / np.sqrt(num_rooms)))

        # Draw rooms with adaptive styling
        for i, room in enumerate(self.floor_plan.rooms):
            if room.x is not None and room.y is not None:
                # Color coding for violations
                if room_violations[room.name] > 0:
                    face_color = 'lightcoral'
                    edge_color = 'darkred'
                    linewidth = violation_line_width
                    alpha = 0.8
                else:
                    face_color = colors[i]
                    edge_color = 'black'
                    linewidth = room_line_width
                    alpha = max(0.4, min(0.7, 1.0 / np.sqrt(num_rooms / 20 + 1)))

                rect = Rectangle(
                    (room.x, room.y),
                    room.width,
                    room.height,
                    linewidth=linewidth,
                    edgecolor=edge_color,
                    facecolor=face_color,
                    alpha=alpha
                )
                self.ax.add_patch(rect)

                # Adaptive text display
                self._draw_room_text(room, base_font_size, show_room_details, show_expansion_info)

        # Simplified constraint visualization for large plans
        constraint_stats = self._draw_constraints_optimized(num_rooms)

        # Set limits and aspect
        self._set_plot_limits()

        # Adaptive title and labels
        title = self._generate_adaptive_title(constraint_stats, num_rooms)
        self.ax.set_title(title, fontsize=title_font_size, fontweight='bold')

        # Show axes labels only for smaller plans
        if num_rooms <= 100:
            self.ax.set_xlabel('Width', fontsize=max(8, base_font_size))
            self.ax.set_ylabel('Height', fontsize=max(8, base_font_size))

        # Adaptive grid
        grid_alpha = max(0.1, min(0.3, 1.0 / np.sqrt(num_rooms / 25 + 1)))
        self.ax.grid(True, alpha=grid_alpha)

        # Smart legend and summary
        self._create_adaptive_legend_and_summary(constraint_stats, num_rooms, base_font_size)

        plt.tight_layout()

        # Add interactive features for room identification
        self._add_room_identification_features(num_rooms)

    def _add_room_identification_features(self, num_rooms):
        """Add interactive features to help identify rooms"""

        # Add click handler for room identification
        def on_click(event):
            if event.inaxes != self.ax:
                return

            # Find room at click location
            clicked_room = None
            for room in self.floor_plan.rooms:
                if (room.x is not None and room.y is not None and
                        room.x <= event.xdata <= room.x + room.width and
                        room.y <= event.ydata <= room.y + room.height):
                    clicked_room = room
                    break

            if clicked_room:
                room_id = self._get_room_id(clicked_room)
                info_text = f"Room {room_id}: {clicked_room.name}"
                if hasattr(clicked_room, 'width'):
                    info_text += f"\nSize: {clicked_room.width}x{clicked_room.height}"
                if hasattr(clicked_room, 'original_width'):
                    info_text += f"\nOriginal: {clicked_room.original_width}x{clicked_room.original_height}"

                # Update title with room info
                current_title = self.ax.get_title()
                if " | Selected: " in current_title:
                    current_title = current_title.split(" | Selected: ")[0]
                self.ax.set_title(f"{current_title} | Selected: {info_text.replace(chr(10), ', ')}")
                plt.draw()

        # Connect the click handler
        if hasattr(self, 'fig'):
            self.fig.canvas.mpl_connect('button_press_event', on_click)

        # For large plans, also create a room index
        if num_rooms > 50:
            self._create_room_index()

    def _create_room_index(self):
        """Create a room index for large floor plans"""
        # Ensure all rooms are mapped before creating index
        self._ensure_all_rooms_mapped()

        print(f"\n=== ROOM INDEX ({len(self.floor_plan.rooms)} rooms) ===")

        # Group rooms by first letter for better organization
        room_groups = {}
        for room in self.floor_plan.rooms:
            first_letter = room.name[0].upper()
            if first_letter not in room_groups:
                room_groups[first_letter] = []
            room_id = self._get_room_id(room)
            room_groups[first_letter].append((room_id, room.name, room.width, room.height))

        # Print organized index
        for letter in sorted(room_groups.keys()):
            print(f"\n{letter}:")
            # Sort by room ID within each letter group
            for room_id, name, width, height in sorted(room_groups[letter]):
                print(f"  {room_id:3d}: {name} ({width}x{height})")

        print(f"\nTotal: {len(self.floor_plan.rooms)} rooms")
        print("Click on any room in the plot to see its details in the title.")

    def get_room_by_id(self, room_id):
        """Helper method to get room by ID number"""
        if not hasattr(self, '_room_id_map'):
            self._room_id_map = {}

        # Ensure all rooms are mapped
        if len(self._room_id_map) != len(self.floor_plan.rooms):
            self._ensure_all_rooms_mapped()

        # Reverse lookup
        for room_name, rid in self._room_id_map.items():
            if rid == room_id:
                return next((r for r in self.floor_plan.rooms if r.name == room_name), None)
        return None

    def _ensure_all_rooms_mapped(self):
        """Ensure all rooms have ID mappings"""
        existing_ids = set(self._room_id_map.values())
        next_id = 1

        for room in self.floor_plan.rooms:
            if room.name not in self._room_id_map:
                while next_id in existing_ids:
                    next_id += 1
                self._room_id_map[room.name] = next_id
                existing_ids.add(next_id)
                next_id += 1

    def print_room_list(self):
        """Print a complete list of rooms with their IDs - useful for debugging"""
        print(f"\n=== COMPLETE ROOM LIST ===")
        for i, room in enumerate(self.floor_plan.rooms, 1):
            print(f"{i:3d}: {room.name} - Size: {room.width}x{room.height} - Position: ({room.x}, {room.y})")
        print(f"Total: {len(self.floor_plan.rooms)} rooms")

    def _calculate_room_violations(self):
        """Efficiently calculate constraint violations for all rooms"""
        room_violations = {}

        for room in self.floor_plan.rooms:
            violations = 0
            if room.name in self.floor_plan.non_adjacency_graph:
                for non_adj_room_name in self.floor_plan.non_adjacency_graph[room.name]:
                    non_adj_room = next((r for r in self.floor_plan.rooms if r.name == non_adj_room_name), None)
                    if non_adj_room and room.has_shared_wall_with(non_adj_room):
                        violations += 1
            room_violations[room.name] = violations

        return room_violations

    def _draw_room_text(self, room, base_font_size, show_details, show_expansion):
        """Draw room text with adaptive detail level and identification methods"""
        num_rooms = len(self.floor_plan.rooms)

        # Calculate if room is large enough for text
        room_area = room.width * room.height
        min_area_for_text = max(4, num_rooms / 50)  # Adaptive minimum area

        if base_font_size < 4 or room_area < min_area_for_text:
            # For very small rooms, use room ID numbers instead of names
            room_id = self._get_room_id(room)
            if room_area >= 2:  # Only show ID if room is not tiny
                self.ax.text(
                    room.x + room.width / 2,
                    room.y + room.height / 2,
                    str(room_id),
                    ha='center',
                    va='center',
                    fontsize=max(6, base_font_size),
                    fontweight='bold',
                    color='black',
                    clip_on=True
                )
            return

        # For larger rooms, show more detail
        display_text = self._get_room_display_text(room, show_details, show_expansion)

        # Adaptive text box styling
        bbox_alpha = max(0.6, min(0.9, 1.0 / np.sqrt(num_rooms / 30 + 1)))

        self.ax.text(
            room.x + room.width / 2,
            room.y + room.height / 2,
            display_text,
            ha='center',
            va='center',
            fontsize=base_font_size,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=bbox_alpha),
            clip_on=True
        )

    def _get_room_id(self, room):
        """Get a unique ID number for the room"""
        if not hasattr(self, '_room_id_map'):
            self._room_id_map = {}

        # If room not in map, add it
        if room.name not in self._room_id_map:
            # Add all rooms that aren't already mapped
            existing_ids = set(self._room_id_map.values())
            next_id = 1

            for r in self.floor_plan.rooms:
                if r.name not in self._room_id_map:
                    # Find next available ID
                    while next_id in existing_ids:
                        next_id += 1
                    self._room_id_map[r.name] = next_id
                    existing_ids.add(next_id)
                    next_id += 1

        return self._room_id_map[room.name]

    def _get_room_display_text(self, room, show_details, show_expansion):
        """Get the display text for a room based on detail level"""
        num_rooms = len(self.floor_plan.rooms)

        if num_rooms > 200:
            # Very large plans: just room ID
            return str(self._get_room_id(room))
        elif num_rooms > 100:
            # Large plans: ID + abbreviated name
            room_id = self._get_room_id(room)
            short_name = room.name[:8] + "..." if len(room.name) > 8 else room.name
            return f"{room_id}\n{short_name}"
        elif num_rooms > 50:
            # Medium plans: ID + name
            room_id = self._get_room_id(room)
            return f"{room_id}: {room.name}"
        else:
            # Small plans: full detail
            display_text = room.name
            if show_details:
                current_size = f"{room.width}x{room.height}"
                display_text = f"{room.name}\n{current_size}"

                if show_expansion and (room.width != room.original_width or room.height != room.original_height):
                    original_size = f"{room.original_width}x{room.original_height}"
                    if room.rotated:
                        display_text += f"\n(from {room.original_height}x{room.original_width})"
                    else:
                        display_text += f"\n(from {original_size})"
            return display_text

    def _draw_constraints_optimized(self, num_rooms):
        """Draw constraint lines with optimization for large room counts"""
        # For very large plans, skip or simplify constraint visualization
        if num_rooms > 200:
            return self._calculate_constraint_stats_only()

        constraint_stats = {
            'adjacent_pairs': [],
            'unsatisfied_adjacencies': [],
            'non_adjacency_satisfied': [],
            'non_adjacency_violated': []
        }

        # Adaptive line styling
        line_alpha = max(0.3, min(0.8, 1.0 / np.sqrt(num_rooms / 20 + 1)))
        line_width = max(0.5, min(2, 15 / np.sqrt(num_rooms)))

        # Show fewer constraint lines for very large plans
        show_all_constraints = num_rooms <= 100
        show_violations_only = num_rooms > 100

        # Process adjacency relationships
        for room1_name, room2_name in self.floor_plan.adjacency_graph.edges:
            room1 = next((r for r in self.floor_plan.rooms if r.name == room1_name), None)
            room2 = next((r for r in self.floor_plan.rooms if r.name == room2_name), None)

            if room1 and room2 and room1.x is not None and room2.x is not None:
                center1 = (room1.x + room1.width / 2, room1.y + room1.height / 2)
                center2 = (room2.x + room2.width / 2, room2.y + room2.height / 2)

                if room1.has_shared_wall_with(room2):
                    constraint_stats['adjacent_pairs'].append((room1_name, room2_name))
                    if show_all_constraints:
                        self.ax.plot([center1[0], center2[0]], [center1[1], center2[1]], 'g-',
                                     linewidth=line_width, alpha=line_alpha)
                else:
                    constraint_stats['unsatisfied_adjacencies'].append((room1_name, room2_name))
                    if show_all_constraints or show_violations_only:
                        self.ax.plot([center1[0], center2[0]], [center1[1], center2[1]], 'r--',
                                     linewidth=line_width * 1.2, alpha=min(0.9, line_alpha * 1.5))

        # Process non-adjacency relationships
        for room1_name, room2_name in self.floor_plan.non_adjacency_graph.edges:
            room1 = next((r for r in self.floor_plan.rooms if r.name == room1_name), None)
            room2 = next((r for r in self.floor_plan.rooms if r.name == room2_name), None)

            if room1 and room2 and room1.x is not None and room2.x is not None:
                center1 = (room1.x + room1.width / 2, room1.y + room1.height / 2)
                center2 = (room2.x + room2.width / 2, room2.y + room2.height / 2)

                if room1.has_shared_wall_with(room2):
                    # Violation - always show these
                    constraint_stats['non_adjacency_violated'].append((room1_name, room2_name))

                    # Violation lines and markers
                    self.ax.plot([center1[0], center2[0]], [center1[1], center2[1]], 'red',
                                 linewidth=line_width * 1.5, linestyle=':', alpha=min(0.9, line_alpha * 1.5))

                    # Show warning markers only for manageable numbers
                    if num_rooms <= 150:
                        marker_size = max(4, min(12, 60 / np.sqrt(num_rooms)))
                        self.ax.plot(center1[0], center1[1], 'rX', markersize=marker_size, alpha=0.9)
                        self.ax.plot(center2[0], center2[1], 'rX', markersize=marker_size, alpha=0.9)
                else:
                    constraint_stats['non_adjacency_satisfied'].append((room1_name, room2_name))
                    if show_all_constraints:
                        self.ax.plot([center1[0], center2[0]], [center1[1], center2[1]],
                                     color='blue', linewidth=line_width, linestyle=':', alpha=line_alpha * 0.7)

        return constraint_stats

    def _calculate_constraint_stats_only(self):
        """Calculate constraint statistics without drawing (for very large plans)"""
        constraint_stats = {
            'adjacent_pairs': [],
            'unsatisfied_adjacencies': [],
            'non_adjacency_satisfied': [],
            'non_adjacency_violated': []
        }

        # Just calculate stats without drawing
        for room1_name, room2_name in self.floor_plan.adjacency_graph.edges:
            room1 = next((r for r in self.floor_plan.rooms if r.name == room1_name), None)
            room2 = next((r for r in self.floor_plan.rooms if r.name == room2_name), None)

            if room1 and room2 and room1.x is not None and room2.x is not None:
                if room1.has_shared_wall_with(room2):
                    constraint_stats['adjacent_pairs'].append((room1_name, room2_name))
                else:
                    constraint_stats['unsatisfied_adjacencies'].append((room1_name, room2_name))

        for room1_name, room2_name in self.floor_plan.non_adjacency_graph.edges:
            room1 = next((r for r in self.floor_plan.rooms if r.name == room1_name), None)
            room2 = next((r for r in self.floor_plan.rooms if r.name == room2_name), None)

            if room1 and room2 and room1.x is not None and room2.x is not None:
                if room1.has_shared_wall_with(room2):
                    constraint_stats['non_adjacency_violated'].append((room1_name, room2_name))
                else:
                    constraint_stats['non_adjacency_satisfied'].append((room1_name, room2_name))

        return constraint_stats

    def _set_plot_limits(self):
        """Set plot limits with padding"""
        max_width = self.floor_plan.floor_width
        max_height = self.floor_plan.floor_height

        # Adaptive padding based on floor size
        padding = max(1, min(5, max(max_width, max_height) * 0.02))

        self.ax.set_xlim(-padding, max_width + padding)
        self.ax.set_ylim(-padding, max_height + padding)
        self.ax.set_aspect('equal')

    def _generate_adaptive_title(self, constraint_stats, num_rooms):
        """Generate title that adapts to room count"""
        if num_rooms <= 50:
            # Detailed title for smaller plans
            title = f'Floor Plan ({num_rooms} rooms) - '
            title += f'Adjacency: {len(constraint_stats["adjacent_pairs"])}/{len(self.floor_plan.adjacency_graph.edges)}'
            if len(self.floor_plan.non_adjacency_graph.edges) > 0:
                title += f', Non-Adjacency: {len(constraint_stats["non_adjacency_satisfied"])}/{len(self.floor_plan.non_adjacency_graph.edges)} satisfied'
        else:
            # Simplified title for large plans
            violations = len(constraint_stats["unsatisfied_adjacencies"]) + len(
                constraint_stats["non_adjacency_violated"])
            if violations > 0:
                title = f'Floor Plan ({num_rooms} rooms) - {violations} constraint violations'
            else:
                title = f'Floor Plan ({num_rooms} rooms) - All constraints satisfied'

        return title

    def _create_adaptive_legend_and_summary(self, constraint_stats, num_rooms, font_size):
        """Create legend and summary that adapt to room count"""

        # Skip detailed legend for very large plans
        if num_rooms > 200:
            self._create_simple_summary(constraint_stats, font_size)
            return

        # Create legend elements based on what's actually shown
        legend_elements = []

        if num_rooms <= 100:  # Full legend for moderate sizes
            if constraint_stats['adjacent_pairs']:
                legend_elements.append(Line2D([0], [0], color='green', linewidth=2,
                                              label=f'Adjacent (satisfied): {len(constraint_stats["adjacent_pairs"])}'))

            if constraint_stats['unsatisfied_adjacencies']:
                legend_elements.append(Line2D([0], [0], color='red', linewidth=2,
                                              linestyle='--', alpha=0.9,
                                              label=f'Adjacent (unsatisfied): {len(constraint_stats["unsatisfied_adjacencies"])}'))

            if len(self.floor_plan.non_adjacency_graph.edges) > 0:
                legend_elements.append(Line2D([0], [0], color='blue', linewidth=2,
                                              linestyle=':', alpha=0.7,
                                              label=f'Non-adjacent constraint: {len(self.floor_plan.non_adjacency_graph.edges)}'))

            if constraint_stats['non_adjacency_violated']:
                legend_elements.append(Line2D([0], [0], color='red', linewidth=3,
                                              linestyle=':', alpha=0.8,
                                              label=f'Non-adjacent (VIOLATED): {len(constraint_stats["non_adjacency_violated"])}'))

        else:  # Simplified legend for larger plans
            violations = len(constraint_stats["unsatisfied_adjacencies"]) + len(
                constraint_stats["non_adjacency_violated"])
            if violations > 0:
                legend_elements.append(Line2D([0], [0], color='red', linewidth=2,
                                              label=f'Constraint violations: {violations}'))

            satisfied = len(constraint_stats["adjacent_pairs"]) + len(constraint_stats["non_adjacency_satisfied"])
            if satisfied > 0:
                legend_elements.append(Line2D([0], [0], color='green', linewidth=2,
                                              label=f'Constraints satisfied: {satisfied}'))

        # Position legend appropriately
        if legend_elements and num_rooms <= 150:
            self.ax.legend(handles=legend_elements, loc='upper left',
                           bbox_to_anchor=(1.02, 1), borderaxespad=0,
                           fontsize=max(6, font_size - 2))

        # Create summary text
        self._create_constraint_summary(constraint_stats, num_rooms, font_size)

    def _create_constraint_summary(self, constraint_stats, num_rooms, font_size):
        """Create constraint summary text with room identification legend"""
        if num_rooms > 300:  # Skip summary for very large plans
            return

        total_constraints = len(self.floor_plan.adjacency_graph.edges) + len(self.floor_plan.non_adjacency_graph.edges)

        summary_text = f"Rooms: {num_rooms}\n"

        if num_rooms <= 100:
            # Detailed summary
            summary_text += f"Adjacency: {len(constraint_stats['adjacent_pairs'])}/{len(self.floor_plan.adjacency_graph.edges)} satisfied\n"
            summary_text += f"Non-adjacency: {len(constraint_stats['non_adjacency_satisfied'])}/{len(self.floor_plan.non_adjacency_graph.edges)} satisfied"

            if constraint_stats['non_adjacency_violated']:
                summary_text += f"\nViolations: {len(constraint_stats['non_adjacency_violated'])} non-adjacency"
        else:
            # Simplified summary
            total_violations = len(constraint_stats["unsatisfied_adjacencies"]) + len(
                constraint_stats["non_adjacency_violated"])
            total_satisfied = len(constraint_stats["adjacent_pairs"]) + len(constraint_stats["non_adjacency_satisfied"])
            if total_constraints > 0:
                summary_text += f"Constraints: {total_satisfied}/{total_constraints} satisfied"
                if total_violations > 0:
                    summary_text += f"\nViolations: {total_violations}"

        # Add identification help for large plans
        if num_rooms > 50:
            summary_text += f"\n\nRoom IDs shown (1-{num_rooms})"
            summary_text += "\nClick plot for room list"

        # Choose background color based on violations
        has_violations = len(constraint_stats["non_adjacency_violated"]) > 0 or len(
            constraint_stats["unsatisfied_adjacencies"]) > 0
        all_satisfied = (len(constraint_stats["adjacent_pairs"]) == len(self.floor_plan.adjacency_graph.edges) and
                         len(constraint_stats["non_adjacency_satisfied"]) == len(
                    self.floor_plan.non_adjacency_graph.edges))

        bg_color = "lightcoral" if has_violations else "lightgreen" if all_satisfied else "lightyellow"

        # Adaptive text size and positioning
        text_font_size = max(6, min(font_size, 12))
        text_alpha = max(0.7, min(0.9, 1.0 / np.sqrt(num_rooms / 50 + 1)))

        self.ax.text(0.02, 0.98, summary_text, transform=self.ax.transAxes,
                     verticalalignment='top',
                     bbox=dict(boxstyle="round,pad=0.3", facecolor=bg_color, alpha=text_alpha),
                     fontsize=text_font_size, fontweight='bold')

    def _create_simple_summary(self, constraint_stats, font_size):
        """Create very simple summary for extremely large plans"""
        total_violations = len(constraint_stats["unsatisfied_adjacencies"]) + len(
            constraint_stats["non_adjacency_violated"])

        if total_violations > 0:
            summary_text = f"{len(self.floor_plan.rooms)} rooms\n{total_violations} violations"
            bg_color = "lightcoral"
        else:
            summary_text = f"{len(self.floor_plan.rooms)} rooms\nAll constraints OK"
            bg_color = "lightgreen"

        self.ax.text(0.02, 0.98, summary_text, transform=self.ax.transAxes,
                     verticalalignment='top',
                     bbox=dict(boxstyle="round,pad=0.3", facecolor=bg_color, alpha=0.8),
                     fontsize=max(8, font_size), fontweight='bold')


def main():
    """Main function to run the GUI"""
    root = tk.Tk()

    # Configure style
    style = ttk.Style()

    # Try to use a modern theme
    try:
        style.theme_use('clam')  # More modern than default
    except:
        pass  # Fall back to default theme

    # Configure some custom styles
    style.configure('Accent.TButton', foreground='white')

    # Create and run the application
    app = FloorPlanGUI(root)

    # Center the window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()



