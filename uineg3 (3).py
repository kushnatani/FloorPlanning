import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from neg3 import FloorPlan  # Import from your original file
import json
from tkinter import filedialog
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
#import matplotlib.patches as mpatches
import math

from shapely.measurement import length


class CADApp:
    def __init__(self, parent, callback):
        self.window = tk.Toplevel(parent)
        self.callback = callback  # Callback to send regions back to main GUI
        self.grid_spacing = tk.IntVar(value=5)
        self.grid_spacing_set = False

        self.window.title("Enhanced CAD Grid Tool")
        self.window.state('zoomed')

        self.unit_spacing = 1
        self.pixels_per_unit = 50
        self.dot_radius = 2
        self.grid_points = []
        self.grid_dots = {}
        self.last_valid_point = None
        self.clicked_coordinates = []
        self.drawn_lines = []
        self.hover_line = None
        self.distance_labels = []
        self.is_closed_shape = False
        self.first_point = None
        self.scaled_coordinates = []

        self.insertion_mode = False
        self.insertion_start_point = None
        self.insertion_end_point = None
        self.insertion_position = None
        self.temp_coordinates = []

        self.setup_ui()
        self.create_grid()
        self.bind_events()

        self.window.bind('<Configure>', self.on_window_resize)

    def setup_ui(self):
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        ttk.Button(control_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Show Coordinates", command=self.show_coordinates).pack(side=tk.LEFT, padx=5)

        ttk.Label(control_frame, text="Grid Spacing:").pack(side=tk.LEFT, padx=5)
        self.grid_entry = ttk.Entry(control_frame, textvariable=self.grid_spacing, width=10)
        self.grid_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Set Grid Spacing", command=self.get_Grid_space).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Finalize", command=self.is_Finalize).pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(control_frame, text="Enter a positive integer grid spacing to start drawing")
        self.status_label.pack(side=tk.RIGHT, padx=10)

        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height() - 100

        self.grid_width_units = max(50, width // self.pixels_per_unit)
        self.grid_height_units = max(30, height // self.pixels_per_unit)

        canvas_width = self.grid_width_units * self.pixels_per_unit + self.pixels_per_unit
        canvas_height = self.grid_height_units * self.pixels_per_unit + self.pixels_per_unit

        self.canvas = tk.Canvas(canvas_frame, bg='white',
                                scrollregion=(-self.pixels_per_unit / 2, -self.pixels_per_unit / 2,
                                              canvas_width, canvas_height))

        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        h_scroll.grid(row=1, column=0, sticky="ew")
        v_scroll.grid(row=0, column=1, sticky="ns")

        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

    def get_Grid_space(self):
        try:
            value = self.grid_spacing.get()
            if value <= 0:
                messagebox.showerror("Invalid Input", "Grid spacing must be a positive integer.")
                return
            self.unit_spacing = value
            self.grid_spacing_set = True
            self.update_status()
            print(f"Grid spacing set to: {self.unit_spacing}")
        except tk.TclError:
            messagebox.showerror("Invalid Input", "Please enter a valid integer for grid spacing.")

    def create_grid(self):
        self.grid_points = []
        self.grid_dots = {}

        for grid_x in range(0, self.grid_width_units + 1):
            for grid_y in range(0, self.grid_height_units + 1):
                pixel_x = grid_x * self.pixels_per_unit
                pixel_y = grid_y * self.pixels_per_unit

                dot = self.canvas.create_oval(
                    pixel_x - self.dot_radius, pixel_y - self.dot_radius,
                    pixel_x + self.dot_radius, pixel_y + self.dot_radius,
                    fill='gray', outline='gray', tags="grid_dot"
                )

                self.grid_points.append((grid_x, grid_y, pixel_x, pixel_y, dot))
                self.grid_dots[(grid_x, grid_y)] = dot

    def bind_events(self):
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_hover)

    def on_window_resize(self, event):
        if event.widget == self.window:
            self.window.after_idle(self.recreate_grid)

    def recreate_grid(self):
        self.canvas.delete("grid_dot")

        width = self.window.winfo_width()
        height = self.window.winfo_height() - 100

        self.grid_width_units = max(50, width // self.pixels_per_unit)
        self.grid_height_units = max(30, height // self.pixels_per_unit)

        canvas_width = self.grid_width_units * self.pixels_per_unit + self.pixels_per_unit
        canvas_height = self.grid_height_units * self.pixels_per_unit + self.pixels_per_unit
        self.canvas.configure(scrollregion=(-self.pixels_per_unit / 2, -self.pixels_per_unit / 2,
                                            canvas_width, canvas_height))

        self.create_grid()

    def on_hover(self, event):
        if not self.grid_spacing_set or self.last_valid_point is None or self.is_closed_shape:
            return

        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        closest_point = self.find_closest_point(x, y)

        if closest_point and (closest_point[0], closest_point[1]) != self.last_valid_point:
            if self.hover_line:
                self.canvas.delete(self.hover_line)
                self.canvas.delete("hover_distance")
                self.hover_line = None

            if self.is_aligned(self.last_valid_point, (closest_point[0], closest_point[1])):
                last_pixel_x = self.last_valid_point[0] * self.pixels_per_unit
                last_pixel_y = self.last_valid_point[1] * self.pixels_per_unit

                self.hover_line = self.canvas.create_line(
                    last_pixel_x, last_pixel_y,
                    closest_point[2], closest_point[3],
                    fill='lightblue', width=1, dash=(5, 5)
                )

                distance = self.calculate_distance(self.last_valid_point, (closest_point[0], closest_point[1]))
                mid_x = (last_pixel_x + closest_point[2]) / 2
                mid_y = (last_pixel_y + closest_point[3]) / 2

                self.canvas.create_text(mid_x, mid_y - 10, text=f"{distance:.0f} units",
                                        fill='blue', tags="hover_distance", font=('Arial', 8))
        else:
            if self.hover_line:
                self.canvas.delete(self.hover_line)
                self.canvas.delete("hover_distance")
                self.hover_line = None

    def on_click(self, event):
        if not self.grid_spacing_set:
            messagebox.showinfo("Grid Spacing Required", "Please set a valid grid spacing before drawing.")
            return

        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        closest_point = self.find_closest_point(x, y)

        if closest_point:
            grid_x, grid_y = closest_point[0], closest_point[1]
            pixel_x, pixel_y = closest_point[2], closest_point[3]

            if self.is_closed_shape and not self.insertion_mode:
                self.status_label.config(text="Shape is closed. Delete edges or reset to continue.")
                return

            if self.insertion_mode:
                self.handle_insertion_click(grid_x, grid_y, pixel_x, pixel_y)
                return

            if (self.first_point is not None and
                    (grid_x, grid_y) == self.first_point and
                    len(self.clicked_coordinates) > 2 and
                    self.last_valid_point is not None and
                    self.is_aligned(self.last_valid_point, (grid_x, grid_y))):
                self.close_shape(grid_x, grid_y, pixel_x, pixel_y)
                return

            self.clicked_coordinates.append((grid_x, grid_y))
            print(
                f"Clicked: Grid({grid_x}, {grid_y}) = Units({grid_x * self.unit_spacing}, {grid_y * self.unit_spacing})")

            if self.last_valid_point is None:
                self.last_valid_point = (grid_x, grid_y)
                if self.first_point is None:
                    self.first_point = (grid_x, grid_y)
                print(f"Starting from grid point: ({grid_x}, {grid_y})")
            else:
                if self.is_aligned(self.last_valid_point, (grid_x, grid_y)):
                    if (grid_x, grid_y) != self.last_valid_point:
                        self.draw_line_with_distance(grid_x, grid_y, pixel_x, pixel_y)
                else:
                    print("Diagonal point - skipped")

            self.update_point_colors()
            self.update_status()

    def handle_insertion_click(self, grid_x, grid_y, pixel_x, pixel_y):
        current_point = (grid_x, grid_y)

        if self.last_valid_point is None:
            if current_point == self.insertion_start_point:
                self.last_valid_point = current_point
                self.temp_coordinates = [current_point]
                print(f"Insertion started from: {current_point}")
                self.update_status()
                return
            else:
                print(f"Must start from the original start point: {self.insertion_start_point}")
                return

        if current_point == self.insertion_end_point:
            self.temp_coordinates.append(current_point)
            self.complete_insertion(pixel_x, pixel_y)
            return

        if self.is_aligned(self.last_valid_point, current_point):
            if current_point != self.last_valid_point and current_point not in self.temp_coordinates:
                self.temp_coordinates.append(current_point)
                self.draw_line_with_distance(grid_x, grid_y, pixel_x, pixel_y)
                print(f"Insertion: Line drawn to ({grid_x}, {grid_y})")
        else:
            print("Diagonal point - skipped in insertion mode")

        self.update_point_colors()
        self.update_status()

    def complete_insertion(self, pixel_x, pixel_y):
        if len(self.temp_coordinates) < 2:
            print("Not enough points for insertion")
            self.cancel_insertion()
            return

        if self.hover_line:
            self.canvas.delete(self.hover_line)
            self.canvas.delete("hover_distance")
            self.hover_line = None

        start_index = self.clicked_coordinates.index(self.insertion_start_point)
        end_index = self.clicked_coordinates.index(self.insertion_end_point)

        self.clicked_coordinates[start_index:end_index + 1] = self.temp_coordinates

        self.update_affected_lines(start_index, end_index)

        print(f"Insertion completed! Added {len(self.temp_coordinates) - 2} new coordinates")
        print(f"New coordinates: {self.temp_coordinates[1:-1]}")

        self.insertion_mode = False
        self.insertion_start_point = None
        self.insertion_end_point = None
        self.insertion_position = None
        self.temp_coordinates = []
        self.last_valid_point = self.insertion_end_point

        self.update_status()
        print("Insertion mode ended. You can continue drawing from the end point.")

    def update_affected_lines(self, start_index, end_index):
        lines_to_remove = []
        for line_data in self.drawn_lines:
            line_start_index = self.clicked_coordinates.index(line_data['start'])
            if start_index <= line_start_index < end_index:
                self.canvas.delete(line_data['line'])
                self.canvas.delete(line_data['distance_label'])
                lines_to_remove.append(line_data)

        for line_data in lines_to_remove:
            self.drawn_lines.remove(line_data)

        self.last_valid_point = self.clicked_coordinates[start_index]
        for i in range(start_index, start_index + len(self.temp_coordinates) - 1):
            start_point = self.clicked_coordinates[i]
            end_point = self.clicked_coordinates[i + 1]

            start_pixel_x = start_point[0] * self.pixels_per_unit
            start_pixel_y = start_point[1] * self.pixels_per_unit
            end_pixel_x = end_point[0] * self.pixels_per_unit
            end_pixel_y = end_point[1] * self.pixels_per_unit

            line = self.canvas.create_line(
                start_pixel_x, start_pixel_y, end_pixel_x, end_pixel_y,
                fill='blue', width=2, tags="drawn_line"
            )

            distance = self.calculate_distance(start_point, end_point)
            mid_x = (start_pixel_x + end_pixel_x) / 2
            mid_y = (start_pixel_y + end_pixel_y) / 2

            distance_label = self.canvas.create_text(
                mid_x + 10, mid_y - 10, text=f"{distance:.0f}",
                fill='darkblue', font=('Arial', 9, 'bold'), tags="distance_label"
            )

            self.drawn_lines.append({
                'line': line,
                'distance_label': distance_label,
                'start': start_point,
                'end': end_point
            })
            self.last_valid_point = end_point

        self.update_point_colors()

    def cancel_insertion(self):
        if self.insertion_mode:
            self.insertion_mode = False
            self.insertion_start_point = None
            self.insertion_end_point = None
            self.insertion_position = None
            self.temp_coordinates = []
            self.last_valid_point = None
            print("Insertion mode cancelled")
            self.update_status()

    def close_shape(self, grid_x, grid_y, pixel_x, pixel_y):
        self.draw_line_with_distance(grid_x, grid_y, pixel_x, pixel_y)
        self.is_closed_shape = True
        self.status_label.config(text="Shape closed! Right-click edges to delete them.")
        print("Shape closed!")

    def draw_line_with_distance(self, grid_x, grid_y, pixel_x, pixel_y):
        last_pixel_x = self.last_valid_point[0] * self.pixels_per_unit
        last_pixel_y = self.last_valid_point[1] * self.pixels_per_unit

        if self.hover_line:
            self.canvas.delete(self.hover_line)
            self.canvas.delete("hover_distance")
            self.hover_line = None

        line = self.canvas.create_line(
            last_pixel_x, last_pixel_y, pixel_x, pixel_y,
            fill='blue', width=2, tags="drawn_line"
        )

        distance = self.calculate_distance(self.last_valid_point, (grid_x, grid_y))
        mid_x = (last_pixel_x + pixel_x) / 2
        mid_y = (last_pixel_y + pixel_y) / 2

        distance_label = self.canvas.create_text(
            mid_x + 10, mid_y - 10, text=f"{distance:.0f}",
            fill='darkblue', font=('Arial', 9, 'bold'), tags="distance_label"
        )

        self.drawn_lines.append({
            'line': line,
            'distance_label': distance_label,
            'start': self.last_valid_point,
            'end': (grid_x, grid_y)
        })

        self.last_valid_point = (grid_x, grid_y)
        if not self.insertion_mode:
            print(f"Line drawn to ({grid_x}, {grid_y}) - Distance: {distance:.0f} units")

    def on_right_click(self, event):
        if not self.grid_spacing_set:
            return

        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        closest_line = None
        min_distance = float('inf')

        for line_data in self.drawn_lines:
            line_distance = self.distance_to_line(x, y, line_data)
            if line_distance < 10 and line_distance < min_distance:
                min_distance = line_distance
                closest_line = line_data

        if closest_line:
            self.delete_line(closest_line)

    def distance_to_line(self, px, py, line_data):
        start_x = line_data['start'][0] * self.pixels_per_unit
        start_y = line_data['start'][1] * self.pixels_per_unit
        end_x = line_data['end'][0] * self.pixels_per_unit
        end_y = line_data['end'][1] * self.pixels_per_unit

        dx = end_x - start_x
        dy = end_y - start_y

        if dx == 0 and dy == 0:
            return math.sqrt((px - start_x) ** 2 + (py - start_y) ** 2)

        t = max(0, min(1, ((px - start_x) * dx + (py - start_y) * dy) / (dx * dx + dy * dy)))

        closest_x = start_x + t * dx
        closest_y = start_y + t * dy

        return math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)

    def delete_line(self, line_data):
        self.canvas.delete(line_data['line'])
        self.canvas.delete(line_data['distance_label'])

        start_point = line_data['start']
        end_point = line_data['end']

        start_index = self.clicked_coordinates.index(start_point)
        end_index = self.clicked_coordinates.index(end_point)

        print(f"Deleted line from {start_point} to {end_point}")

        self.drawn_lines.remove(line_data)

        if end_index == start_index + 1:
            self.insertion_mode = True
            self.insertion_start_point = start_point
            self.insertion_end_point = end_point
            self.insertion_position = start_index
            self.last_valid_point = None

            print(f"Entering insertion mode: Start from {start_point}, end at {end_point}")
            print("Click on the start point to begin inserting new edges")
        else:
            self.reset_drawing_state_after_deletion()

        if self.is_closed_shape:
            self.is_closed_shape = False

        self.update_point_colors()
        self.update_status()

    def reset_drawing_state_after_deletion(self):
        self.last_valid_point = None
        self.first_point = None

    def point_has_connections(self, point):
        for line_data in self.drawn_lines:
            if line_data['start'] == point or line_data['end'] == point:
                return True
        return False

    def get_connected_points(self):
        connected_points = set()
        for line_data in self.drawn_lines:
            connected_points.add(line_data['start'])
            connected_points.add(line_data['end'])
        return connected_points

    def update_point_colors(self):
        connected_points = self.get_connected_points()

        for point in self.grid_points:
            point_coord = (point[0], point[1])

            if self.insertion_mode:
                if point_coord == self.insertion_start_point:
                    self.canvas.itemconfig(point[4], fill='lime', outline='lime')
                elif point_coord == self.insertion_end_point:
                    self.canvas.itemconfig(point[4], fill='orange', outline='orange')
                elif point_coord in connected_points:
                    self.canvas.itemconfig(point[4], fill='red', outline='red')
                elif point_coord == self.last_valid_point:
                    self.canvas.itemconfig(point[4], fill='blue', outline='blue')
                else:
                    self.canvas.itemconfig(point[4], fill='gray', outline='gray')
            else:
                if point_coord in connected_points:
                    self.canvas.itemconfig(point[4], fill='red', outline='red')
                elif (point_coord == self.first_point and
                      self.first_point is not None and
                      self.first_point != self.last_valid_point and
                      len(self.drawn_lines) > 0):
                    self.canvas.itemconfig(point[4], fill='green', outline='green')
                elif point_coord == self.last_valid_point and self.last_valid_point is not None:
                    self.canvas.itemconfig(point[4], fill='red', outline='red')
                else:
                    self.canvas.itemconfig(point[4], fill='gray', outline='gray')

    def find_closest_point(self, x, y):
        min_dist = float('inf')
        closest = None

        for point in self.grid_points:
            dist = math.sqrt((point[2] - x) ** 2 + (point[3] - y) ** 2)
            if dist < self.dot_radius * 4 and dist < min_dist:
                min_dist = dist
                closest = point
        return closest

    def is_aligned(self, p1, p2):
        return p1[0] == p2[0] or p1[1] == p2[1]

    def calculate_distance(self, p1, p2):
        grid_distance = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
        return grid_distance * self.unit_spacing

    def clear_all(self):
        self.canvas.delete("drawn_line")
        self.canvas.delete("distance_label")
        self.canvas.delete("hover_distance")

        if self.hover_line:
            self.canvas.delete(self.hover_line)
            self.hover_line = None

        self.last_valid_point = None
        self.first_point = None
        self.clicked_coordinates = []
        self.drawn_lines = []
        self.distance_labels = []
        self.is_closed_shape = False

        self.insertion_mode = False
        self.insertion_start_point = None
        self.insertion_end_point = None
        self.insertion_position = None
        self.temp_coordinates = []

        for point in self.grid_points:
            self.canvas.itemconfig(point[4], fill='gray', outline='gray')

        self.update_status()
        print("All cleared!")

    def is_Finalize(self):
        # if not self.is_closed_shape:
        #     messagebox.showerror("Error", "Please close the shape before finalizing.")
        #     return

        self.scaled_coordinates.clear()
        for a, b in self.clicked_coordinates:
            scaled_point = (a * self.unit_spacing, b * self.unit_spacing)
            self.scaled_coordinates.append(scaled_point)

        mini_x = 999
        mini_y = 999
        for a, b in self.scaled_coordinates:
            if (a < mini_x):
                mini_x = a
            if (b < mini_y):
                mini_y = b

        self.scaled_coordinates = [
            (a - mini_x, b - mini_y) for a, b in self.scaled_coordinates
        ]

        # Convert boundary to regions
        regions = self.decompose_into_rectangles()
        if regions:
            # Send regions back to main GUI and close CAD window
            self.callback(regions)
            self.window.destroy()
        else:
            messagebox.showerror("Error", "Failed to generate valid regions from boundary.")

    def decompose_into_rectangles(self):
        """
        Automatically decomposes the polygon defined by self.scaled_coordinates into rectangular regions.
        Stores the regions in self.regions as dictionaries with x, y, width, and height.
        """
        self.regions = []

        # Get unique x-coordinates and y-coordinates from the vertices, sorted
        x_coords = sorted(set(x for x, y in self.scaled_coordinates))
        y_coords = sorted(set(y for x, y in self.scaled_coordinates))

        def point_in_polygon(x, y, polygon):
            """Check if point (x, y) is inside the polygon using ray casting algorithm"""
            n = len(polygon)
            inside = False

            p1x, p1y = polygon[0]
            for i in range(1, n + 1):
                p2x, p2y = polygon[i % n]
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
                p1x, p1y = p2x, p2y

            return inside

        # For each pair of consecutive x-coordinates, create a vertical strip
        for i in range(len(x_coords) - 1):
            x_left = x_coords[i]
            x_right = x_coords[i + 1]
            width = x_right - x_left

            # Find continuous y-ranges within this x-strip that are inside the polygon
            y_ranges = []

            # Check each y-interval
            for j in range(len(y_coords) - 1):
                y_bottom = y_coords[j]
                y_top = y_coords[j + 1]

                # Test if the center of this rectangular cell is inside the polygon
                test_x = (x_left + x_right) / 2
                test_y = (y_bottom + y_top) / 2

                if point_in_polygon(test_x, test_y, self.scaled_coordinates):
                    y_ranges.append((y_bottom, y_top))

            # Merge consecutive y-ranges to form larger rectangles
            if y_ranges:
                merged_ranges = []
                current_start = y_ranges[0][0]
                current_end = y_ranges[0][1]

                for y_start, y_end in y_ranges[1:]:
                    if y_start == current_end:  # Consecutive ranges
                        current_end = y_end
                    else:  # Gap found, finalize current range and start new one
                        merged_ranges.append((current_start, current_end))
                        current_start = y_start
                        current_end = y_end

                # Add the last range
                merged_ranges.append((current_start, current_end))

                # Create rectangles from merged ranges
                for y_start, y_end in merged_ranges:
                    height = y_end - y_start
                    if height > 0 and width > 0:
                        self.regions.append({
                            'x': x_left,  # Left edge x-coordinate
                            'y': y_end,  # Top edge y-coordinate (4th corner)
                            'width': width,  # Width of rectangle
                            'height': height  # Height of rectangle
                        })

        # Normalize y-coordinates by subtracting the minimum y value
        if self.regions:
            min_y = min(region['y'] for region in self.regions)
            for region in self.regions:
                region['y'] = region['y'] - min_y

        return self.regions

    def show_coordinates(self):
        print("\n=== All Clicked Points ===")
        for i, coords in enumerate(self.clicked_coordinates):
            actual_units = (coords[0] * self.unit_spacing, coords[1] * self.unit_spacing)
            print(f"Point {i + 1}: Grid({coords[0]}, {coords[1]}) = Units{actual_units}")
        print("==========================\n")

        coord_window = tk.Toplevel(self.window)
        coord_window.title("Clicked Coordinates")
        coord_window.geometry("450x400")

        text_widget = tk.Text(coord_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)

        text_widget.insert(tk.END, f"All Clicked Points (Unit spacing: {self.unit_spacing}):\n\n")
        for i, coords in enumerate(self.clicked_coordinates):
            actual_units = (coords[0] * self.unit_spacing, coords[1] * self.unit_spacing)
            text_widget.insert(tk.END, f"Point {i + 1}: Grid({coords[0]}, {coords[1]}) = Units{actual_units}\n")

        if self.drawn_lines:
            text_widget.insert(tk.END, f"\nTotal Lines: {len(self.drawn_lines)}\n")
            text_widget.insert(tk.END, "Lines with distances:\n")
            for i, line_data in enumerate(self.drawn_lines):
                distance = self.calculate_distance(line_data['start'], line_data['end'])
                start_units = (line_data['start'][0] * self.unit_spacing, line_data['start'][1] * self.unit_spacing)
                end_units = (line_data['end'][0] * self.unit_spacing, line_data['end'][1] * self.unit_spacing)
                text_widget.insert(tk.END, f"Line {i + 1}: {start_units} → {end_units} = {distance:.0f} units\n")

        text_widget.config(state=tk.DISABLED)

    def update_status(self):
        if not self.grid_spacing_set:
            text = "Enter a positive integer grid spacing to start drawing"
        elif self.insertion_mode:
            if self.last_valid_point is None:
                text = f"INSERTION MODE: Click on the start point {self.insertion_start_point} to begin"
            else:
                text = f"INSERTION MODE: Drawing from {self.insertion_start_point} to {self.insertion_end_point} | Points added: {len(self.temp_coordinates) - 1}"
        elif self.is_closed_shape:
            text = "Shape is closed. Right-click edges to delete."
        elif self.last_valid_point is None:
            text = f"Click on any grid point to start drawing (Grid spacing: {self.unit_spacing} units)"
        else:
            text = f"Continue from current point - Points: {len(self.clicked_coordinates)} | Lines: {len(self.drawn_lines)}"
        self.status_label.config(text=text)


class FloorPlanGUI:
    def __init__(self, root):
        self.root = root

        self.root.title("Floor Plan Designer")
        self.root.geometry("1200x800")

        self.floor_plan = None
        self.current_screen = "regions"

        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.nav_frame = ttk.Frame(self.main_frame)
        self.nav_frame.pack(fill=tk.X, pady=(0, 10))

        self.nav_buttons = {}
        nav_items = [
            ("Region Specs", "regions"),
            ("Rooms", "rooms"),
            ("Adjacency", "adjacency"),
            ("Non-Adjacency", "non_adjacency"),
            ("Output", "output")
        ]

        for i, (text, screen) in enumerate(nav_items):
            btn = ttk.Button(self.nav_frame, text=text,
                             command=lambda s=screen: self.show_screen(s))
            btn.pack(side=tk.LEFT, padx=5)
            self.nav_buttons[screen] = btn

        ttk.Button(self.nav_frame, text="Generate Floor Plan",
                   command=self.generate_floor_plan,
                   style="Accent.TButton").pack(side=tk.RIGHT, padx=5)

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.screens = {}
        self.init_screens()

        self.load_example_data()

        self.show_screen("regions")

    def init_screens(self):
        self.init_regions_screen()
        self.init_rooms_screen()
        self.init_adjacency_screen()
        self.init_non_adjacency_screen()
        self.init_output_screen()

    def init_regions_screen(self):
        frame = ttk.Frame(self.content_frame)
        self.screens["regions"] = frame

        ttk.Label(frame, text="Floor Region Specifications",
                  font=("Arial", 16, "bold")).pack(pady=(0, 20))

        instructions = ttk.Label(frame,
                                 text="Click 'Draw Boundary' to open the CAD tool and draw the floor boundary. Finalize to generate regions.",
                                 wraplength=800)
        instructions.pack(pady=(0, 10))

        regions_frame = ttk.LabelFrame(frame, text="Regions", padding=10)
        regions_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        columns = ("X", "Y", "Width", "Height")
        self.regions_tree = ttk.Treeview(regions_frame, columns=columns, show="tree headings", height=8)

        self.regions_tree.heading("#0", text="Region")
        self.regions_tree.column("#0", width=80)
        for col in columns:
            self.regions_tree.heading(col, text=col)
            self.regions_tree.column(col, width=80)

        self.regions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        regions_scrollbar = ttk.Scrollbar(regions_frame, orient=tk.VERTICAL, command=self.regions_tree.yview)
        regions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.regions_tree.config(yscrollcommand=regions_scrollbar.set)


        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Draw Boundary", command=self.launch_cad_tool).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear All", command=self.clear_regions).pack(side=tk.LEFT, padx=5)

    def launch_cad_tool(self):
        CADApp(self.root, self.update_regions_from_cad)

    def update_regions_from_cad(self, regions):
        self.clear_regions()
        for i, region in enumerate(regions):
            item = self.regions_tree.insert("", "end", text=f"Region {i + 1}")
            self.regions_tree.set(item, "X", region['x'])
            self.regions_tree.set(item, "Y", region['y'])
            self.regions_tree.set(item, "Width", region['width'])
            self.regions_tree.set(item, "Height", region['height'])

    def init_rooms_screen(self):
        frame = ttk.Frame(self.content_frame)
        self.screens["rooms"] = frame

        ttk.Label(frame, text="Room Specifications",
                  font=("Arial", 16, "bold")).pack(pady=(0, 20))

        instructions = ttk.Label(frame,
                                 text="Define rooms with their dimensions and maximum expansion limits.",
                                 wraplength=800)
        instructions.pack(pady=(0, 10))

        rooms_frame = ttk.LabelFrame(frame, text="Rooms", padding=10)
        rooms_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        columns = ("Width", "Height", "Max Expansion")
        self.rooms_tree = ttk.Treeview(rooms_frame, columns=columns, show="tree headings", height=8)
        self.rooms_tree.bind("<Double-1>", lambda event: self.edit_room())
        self.rooms_tree.heading("#0", text="Room Name")
        self.rooms_tree.column("#0", width=120)
        for col in columns:
            self.rooms_tree.heading(col, text=col)
            self.rooms_tree.column(col, width=100)

        self.rooms_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        rooms_scrollbar = ttk.Scrollbar(rooms_frame, orient=tk.VERTICAL, command=self.rooms_tree.yview)
        rooms_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rooms_tree.config(yscrollcommand=rooms_scrollbar.set)

        single_input_frame = ttk.LabelFrame(frame, text="Add Single Room", padding=10)
        single_input_frame.pack(fill=tk.X, pady=5)

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

        ttk.Button(single_input_frame, text="Add Room", command=self.add_room).grid(row=0, column=8, padx=10)

        bulk_input_frame = ttk.LabelFrame(frame, text="Add Multiple Rooms", padding=10)
        bulk_input_frame.pack(fill=tk.X, pady=5)

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

        ttk.Button(bulk_input_frame, text="Add Multiple Rooms", command=self.add_bulk_rooms).grid(row=0, column=10,
                                                                                                  padx=10)

        management_frame = ttk.Frame(frame)
        management_frame.pack(fill=tk.X, pady=10)

        ttk.Button(management_frame, text="Remove Selected", command=self.remove_room).pack(side=tk.LEFT, padx=5)
        ttk.Button(management_frame, text="Edit Selected", command=self.edit_room).pack(side=tk.LEFT, padx=5)
        ttk.Button(management_frame, text="Clear All", command=self.clear_rooms).pack(side=tk.LEFT, padx=5)

    def init_adjacency_screen(self):
        frame = ttk.Frame(self.content_frame)
        self.screens["adjacency"] = frame

        ttk.Label(frame, text="Room Adjacency Requirements",
                  font=("Arial", 16, "bold")).pack(pady=(0, 20))

        instructions = ttk.Label(frame,
                                 text="Define which rooms should be adjacent to each other (share a wall).",
                                 wraplength=800)
        instructions.pack(pady=(0, 10))

        main_container = ttk.Frame(frame)
        main_container.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.LabelFrame(main_container, text="Add Adjacency", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        ttk.Label(left_frame, text="Room 1:").pack(anchor=tk.W)
        self.room1_combo = ttk.Combobox(left_frame, state="readonly", width=20)
        self.room1_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(left_frame, text="Room 2:").pack(anchor=tk.W)
        self.room2_combo = ttk.Combobox(left_frame, state="readonly", width=20)
        self.room2_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(left_frame, text="Add Adjacency", command=self.add_adjacency).pack(pady=10)

        right_frame = ttk.LabelFrame(main_container, text="Current Adjacencies", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.adjacencies_listbox = tk.Listbox(right_frame, height=15)
        self.adjacencies_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        adj_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.adjacencies_listbox.yview)
        adj_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.adjacencies_listbox.config(yscrollcommand=adj_scrollbar.set)

        adj_button_frame = ttk.Frame(right_frame)
        adj_button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(adj_button_frame, text="Remove Selected",
                   command=self.remove_adjacency).pack(side=tk.LEFT, padx=2)
        ttk.Button(adj_button_frame, text="Clear All",
                   command=self.clear_adjacencies).pack(side=tk.LEFT, padx=2)

    def init_non_adjacency_screen(self):
        frame = ttk.Frame(self.content_frame)
        self.screens["non_adjacency"] = frame

        ttk.Label(frame, text="Room Non-Adjacency Requirements",
                  font=("Arial", 16, "bold")).pack(pady=(0, 20))

        instructions = ttk.Label(frame,
                                 text="Define which rooms should NOT be adjacent to each other (should not share a wall).",
                                 wraplength=800)
        instructions.pack(pady=(0, 10))

        main_container = ttk.Frame(frame)
        main_container.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.LabelFrame(main_container, text="Add Non-Adjacency", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        ttk.Label(left_frame, text="Room 1:").pack(anchor=tk.W)
        self.non_adj_room1_combo = ttk.Combobox(left_frame, state="readonly", width=20)
        self.non_adj_room1_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(left_frame, text="Room 2:").pack(anchor=tk.W)
        self.non_adj_room2_combo = ttk.Combobox(left_frame, state="readonly", width=20)
        self.non_adj_room2_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(left_frame, text="Add Non-Adjacency", command=self.add_non_adjacency).pack(pady=10)

        right_frame = ttk.LabelFrame(main_container, text="Current Non-Adjacencies", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.non_adjacencies_listbox = tk.Listbox(right_frame, height=15)
        self.non_adjacencies_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        non_adj_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.non_adjacencies_listbox.yview)
        non_adj_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.non_adjacencies_listbox.config(yscrollcommand=non_adj_scrollbar.set)

        non_adj_button_frame = ttk.Frame(right_frame)
        non_adj_button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(non_adj_button_frame, text="Remove Selected",
                   command=self.remove_non_adjacency).pack(side=tk.LEFT, padx=2)
        ttk.Button(non_adj_button_frame, text="Clear All",
                   command=self.clear_non_adjacencies).pack(side=tk.LEFT, padx=2)

    def init_output_screen(self):
        frame = ttk.Frame(self.content_frame)
        self.screens["output"] = frame
        self.add_mode = tk.StringVar(value="none")

        ttk.Label(frame, text="Floor Plan Output",
                  font=("Arial", 16, "bold")).pack(pady=(0, 20))

        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=1)

        controls_frame = ttk.LabelFrame(left_panel, text="Generation Controls", padding=10)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        gen_controls_row = ttk.Frame(controls_frame)
        gen_controls_row.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(gen_controls_row, text="Add Door", command=lambda: self.add_mode.set("door")).grid(row=0, column=4,
                                                                                                      padx=5)
        ttk.Button(gen_controls_row, text="Add Window", command=lambda: self.add_mode.set("window")).grid(row=0,
                                                                                                          column=5,
                                                                                                          padx=5)

        ttk.Label(gen_controls_row, text="Max Attempts:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.max_attempts_var = tk.StringVar(value="1000")
        ttk.Entry(gen_controls_row, textvariable=self.max_attempts_var, width=10).grid(row=0, column=1, padx=5)

        self.enable_expansion_var = tk.BooleanVar(value=True)
        self.enable_space_optimization_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(gen_controls_row, text="Enable Room Expansion",
                        variable=self.enable_expansion_var).grid(row=0, column=2, padx=20)
        ttk.Checkbutton(gen_controls_row, text="Enable Space Optimization",
                        variable=self.enable_space_optimization_var).grid(row=0, column=3, padx=20)

        save_controls_row = ttk.Frame(controls_frame)
        save_controls_row.pack(fill=tk.X)

        ttk.Button(save_controls_row, text="Save as JSON",
                   command=self.save_floor_plan_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_controls_row, text="Load from JSON",
                   command=self.load_floor_plan_json).pack(side=tk.LEFT, padx=5)

        stats_frame = ttk.LabelFrame(left_panel, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True)

        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=20, width=40)
        self.stats_text.pack(fill=tk.BOTH, expand=True)

        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=2)

        viz_frame = ttk.LabelFrame(right_panel, text="Floor Plan Visualization", padding=10)
        viz_frame.pack(fill=tk.BOTH, expand=True)

        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, viz_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect("button_press_event", self.on_canvas_click)

    def get_non_adjacencies_data(self):
        non_adjacencies = []
        for i in range(self.non_adjacencies_listbox.size()):
            non_adjacency_text = self.non_adjacencies_listbox.get(i)
            room1, room2 = non_adjacency_text.split(" ✗ ")  # Use ✗ instead of Ã¢ï¿½ï¿½
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
        room_found = None

        # Detect wall
        for room in self.floor_plan.rooms:
            if room.x is not None and room.y is not None:
                if abs(y - room.y) < 0.5 and room.x <= x <= room.x + room.width:
                    wall = "bottom"
                    room_found = room
                elif abs(y - (room.y + room.height)) < 0.5 and room.x <= x <= room.x + room.width:
                    wall = "top"
                    room_found = room
                elif abs(x - room.x) < 0.5 and room.y <= y <= room.y + room.height:
                    wall = "left"
                    room_found = room
                elif abs(x - (room.x + room.width)) < 0.5 and room.y <= y <= room.y + room.height:
                    wall = "right"
                    room_found = room
                if wall:
                    break

        if not wall or not room_found:
            return  # Skip if no valid wall found

      #  width = 0.9 # ✅ 2 feet door
        width = 2.000  # ✅ exactly 2 feet in meters = 0.6096

        color = "brown"
        thickness = 3
        arc_color = "gray"

        # Normalize position to keep door fully inside wall
        if wall in ["top", "bottom"]:
            x = max(room_found.x + width / 2, min(x, room_found.x + room_found.width - width / 2))
        else:
            y = max(room_found.y + width / 2, min(y, room_found.y + room_found.height - width / 2))

        # Drawing based on wall
        if wall == "bottom":
            self.ax.plot([x, x], [y, y + width], color=color, linewidth=thickness)
            self.ax.plot([x, x + width], [y, y], color=color, linewidth=thickness)
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
        room_found = None

        # Detect which wall is clicked
        for room in self.floor_plan.rooms:
            if room.x is not None and room.y is not None:
                if abs(y - room.y) < 0.5 and room.x <= x <= room.x + room.width:
                    wall = "bottom"
                    room_found = room
                elif abs(y - (room.y + room.height)) < 0.5 and room.x <= x <= room.x + room.width:
                    wall = "top"
                    room_found = room
                elif abs(x - room.x) < 0.5 and room.y <= y <= room.y + room.height:
                    wall = "left"
                    room_found = room
                elif abs(x - (room.x + room.width)) < 0.5 and room.y <= y <= room.y + room.height:
                    wall = "right"
                    room_found = room
                if wall:
                    break

        if not wall or not room_found:
            return  # Do nothing if no valid wall

        length = 3.000 # ✅ exactly 3 feet
        half = length / 2
        spacing = 0.1
        color = "blue"
        thickness = 2.5
        cap_thickness = 1.5

        # Normalize position to keep window on wall
        if wall in ["top", "bottom"]:
            x = max(room_found.x + half, min(x, room_found.x + room_found.width - half))
        elif wall in ["left", "right"]:
            y = max(room_found.y + half, min(y, room_found.y + room_found.height - half))

        # Drawing logic
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

        # Save window info
        if not hasattr(self, 'placed_windows'):
            self.placed_windows = []
        self.placed_windows.append({"x": x, "y": y, "wall": wall})
        self.canvas.draw()

    def save_floor_plan_json(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Save Floor Plan"
            )

            if not file_path:
                return

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

            if self.floor_plan:
                data["results"] = self.get_floor_plan_results()

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Success", f"Floor plan saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save floor plan:\n{str(e)}")

    def load_floor_plan_json(self):
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Load Floor Plan"
            )

            if not file_path:
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.clear_all_data()

            if "regions" in data:
                for i, region in enumerate(data["regions"]):
                    item = self.regions_tree.insert("", "end", text=f"Region {i + 1}")
                    self.regions_tree.set(item, "X", region['x'])
                    self.regions_tree.set(item, "Y", region['y'])
                    self.regions_tree.set(item, "Width", region['width'])
                    self.regions_tree.set(item, "Height", region['height'])

            if "rooms" in data:
                for room in data["rooms"]:
                    item = self.rooms_tree.insert("", "end", text=room['name'])
                    self.rooms_tree.set(item, "Width", room['width'])
                    self.rooms_tree.set(item, "Height", room['height'])
                    self.rooms_tree.set(item, "Max Expansion", room['max_expansion'])

            if "adjacencies" in data:
                for adj in data["adjacencies"]:
                    self.adjacencies_listbox.insert(tk.END, f"{adj['room1']} â�� {adj['room2']}")

            if "generation_settings" in data:
                settings = data["generation_settings"]
                self.max_attempts_var.set(str(settings.get("max_attempts", 1000)))
                self.enable_expansion_var.set(settings.get("enable_expansion", True))

            has_results = "results" in data and data["results"] is not None

            if has_results:
                response = messagebox.askyesno(
                    "Restore Results",
                    "This file contains previous floor plan results.\n\n"
                    "Do you want to:\n"
                    "â�¢ YES: Restore the exact previous layout\n"
                    "â�¢ NO: Generate a new layout with current settings"
                )

                if response:
                    self.restore_floor_plan_from_results(data["results"])
                    messagebox.showinfo("Success", f"Floor plan and results restored from:\n{file_path}")
                else:
                    self.generate_floor_plan()
                    messagebox.showinfo("Success",
                                        f"Floor plan configuration loaded from:\n{file_path}\nNew layout generated.")
            else:
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
        try:
            regions = self.get_regions_data()
            if not regions:
                raise ValueError("No regions defined")

            self.floor_plan = FloorPlan(regions)

            room_names = []
            for item in self.rooms_tree.get_children():
                name = self.rooms_tree.item(item)['text']
                width = int(self.rooms_tree.set(item, "Width"))
                height = int(self.rooms_tree.set(item, "Height"))
                max_exp = int(self.rooms_tree.set(item, "Max Expansion"))

                self.floor_plan.add_room(name, width, height, max_exp)
                room_names.append(name)

            for i in range(self.adjacencies_listbox.size()):
                adjacency = self.adjacencies_listbox.get(i)
                room1, room2 = adjacency.split(" â�� ")
                self.floor_plan.add_adjacency(room1, room2)

            if "room_placements" in results_data:
                for placement in results_data["room_placements"]:
                    room = next((r for r in self.floor_plan.rooms if r.name == placement["name"]), None)
                    if room:
                        room.x = placement["x"]
                        room.y = placement["y"]
                        room.width = placement["width"]
                        room.height = placement["height"]
                        room.rotated = placement.get("rotated", False)

                        if not hasattr(room, 'original_width'):
                            room.original_width = placement.get("original_width", placement["width"])
                            room.original_height = placement.get("original_height", placement["height"])

            self.update_output_display()

        except Exception as e:
            messagebox.showwarning("Restoration Failed",
                                   f"Could not restore exact layout: {str(e)}\n"
                                   "Generating new layout instead...")
            self.generate_floor_plan()

    def get_regions_data(self):
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
        adjacencies = []
        for i in range(self.adjacencies_listbox.size()):
            adjacency_text = self.adjacencies_listbox.get(i)
            room1, room2 = adjacency_text.split(" â�� ")
            adjacencies.append({"room1": room1, "room2": room2})
        return adjacencies

    def get_floor_plan_results(self):
        if not self.floor_plan:
            return None

        total_area = sum(region['width'] * region['height'] for region in self.floor_plan.floor_regions)
        used_area = sum(room.width * room.height for room in self.floor_plan.rooms if room.x is not None)
        score, adjacent_pairs, violations = self.floor_plan.evaluate_adjacency_score()

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
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def show_screen(self, screen_name):
        for screen in self.screens.values():
            screen.pack_forget()

        if screen_name in self.screens:
            self.screens[screen_name].pack(fill=tk.BOTH, expand=True)
            self.current_screen = screen_name

            for name, btn in self.nav_buttons.items():
                if name == screen_name:
                    btn.state(['pressed'])
                else:
                    btn.state(['!pressed'])

            if screen_name == "adjacency":
                self.refresh_room_combos()
            elif screen_name == "non_adjacency":
                self.refresh_non_adjacency_combos()

    def refresh_non_adjacency_combos(self):
        room_names = [self.rooms_tree.item(item)['text'] for item in self.rooms_tree.get_children()]
        self.non_adj_room1_combo['values'] = room_names
        self.non_adj_room2_combo['values'] = room_names

    def add_non_adjacency(self):
        room1 = self.non_adj_room1_combo.get()
        room2 = self.non_adj_room2_combo.get()

        if not room1 or not room2:
            messagebox.showerror("Error", "Please select both rooms")
            return

        if room1 == room2:
            messagebox.showerror("Error", "A room cannot be non-adjacent to itself")
            return

        non_adjacency1 = f"{room1} ✗ {room2}"  # Use ✗ instead of â†”
        non_adjacency2 = f"{room2} ✗ {room1}"  # Use ✗ instead of â†”

        for i in range(self.non_adjacencies_listbox.size()):
            existing = self.non_adjacencies_listbox.get(i)
            if existing == non_adjacency1 or existing == non_adjacency2:
                messagebox.showerror("Error", "This non-adjacency already exists")
                return

        self.non_adjacencies_listbox.insert(tk.END, non_adjacency1)

        self.non_adj_room1_combo.set("")
        self.non_adj_room2_combo.set("")

    def remove_non_adjacency(self):
        selection = self.non_adjacencies_listbox.curselection()
        if selection:
            self.non_adjacencies_listbox.delete(selection[0])

    def clear_non_adjacencies(self):
        self.non_adjacencies_listbox.delete(0, tk.END)

    def load_example_data(self):
        self.clear_all_data()

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
            self.adjacencies_listbox.insert(tk.END, f"{room1} â�� {room2}")

    def clear_all_data(self):
        for item in self.regions_tree.get_children():
            self.regions_tree.delete(item)

        for item in self.rooms_tree.get_children():
            self.rooms_tree.delete(item)

        self.adjacencies_listbox.delete(0, tk.END)
        self.non_adjacencies_listbox.delete(0, tk.END)

    def add_region(self):
        try:
            x = int(self.region_x_var.get())
            y = int(self.region_y_var.get())
            width = int(self.region_width_var.get())
            height = int(self.region_height_var.get())

            if width <= 0 or height <= 0:
                messagebox.showerror("Error", "Width and height must be positive")
                return

            region_count = len(self.regions_tree.get_children()) + 1
            item = self.regions_tree.insert("", "end", text=f"Region {region_count}")
            self.regions_tree.set(item, "X", x)
            self.regions_tree.set(item, "Y", y)
            self.regions_tree.set(item, "Width", width)
            self.regions_tree.set(item, "Height", height)

            self.region_x_var.set("")
            self.region_y_var.set("")
            self.region_width_var.set("")
            self.region_height_var.set("")

        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    def remove_region(self):
        selected = self.regions_tree.selection()
        if selected:
            self.regions_tree.delete(selected[0])

    def edit_region(self):
        selected = self.regions_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a region to edit")
            return

        item = selected[0]
        current_x = self.regions_tree.set(item, "X")
        current_y = self.regions_tree.set(item, "Y")
        current_width = self.regions_tree.set(item, "Width")
        current_height = self.regions_tree.set(item, "Height")

        self.region_x_var.set(current_x)
        self.region_y_var.set(current_y)
        self.region_width_var.set(current_width)
        self.region_height_var.set(current_height)

        region_name = self.regions_tree.item(item)['text']
        self.regions_tree.delete(item)

        messagebox.showinfo("Edit Mode",
                            f"Region values loaded into input fields.\nModify the values and click 'Add Region' to save changes.\n\nNote: {region_name} has been temporarily removed.")

    def clear_regions(self):
        for item in self.regions_tree.get_children():
            self.regions_tree.delete(item)

    def edit_room(self):
        selected = self.rooms_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a room to edit")
            return

        self.edit_context = {
            'selected_item': selected[0],
            'current_name': self.rooms_tree.item(selected[0])['text'],
            'current_width': self.rooms_tree.set(selected[0], "Width"),
            'current_height': self.rooms_tree.set(selected[0], "Height"),
            'current_max_exp': self.rooms_tree.set(selected[0], "Max Expansion")
        }

        self.edit_window = tk.Toplevel(self.root)
        self.edit_window.title("Edit Room")
        self.edit_window.geometry("400x300")
        self.edit_window.resizable(False, False)
        self.edit_window.transient(self.root)
        self.edit_window.grab_set()

        self.edit_window.update_idletasks()
        x = (self.edit_window.winfo_screenwidth() // 2) - (self.edit_window.winfo_width() // 2)
        y = (self.edit_window.winfo_screenheight() // 2) - (self.edit_window.winfo_height() // 2)
        self.edit_window.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(self.edit_window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Edit Room Properties",
                  font=("Arial", 12, "bold")).pack(pady=(0, 10))

        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.X, pady=5)

        ttk.Label(fields_frame, text="Room Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.edit_name_var = tk.StringVar(value=self.edit_context['current_name'])
        name_entry = ttk.Entry(fields_frame, textvariable=self.edit_name_var, width=20)
        name_entry.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.W)

        ttk.Label(fields_frame, text="Width:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.edit_width_var = tk.StringVar(value=self.edit_context['current_width'])
        width_entry = ttk.Entry(fields_frame, textvariable=self.edit_width_var, width=20)
        width_entry.grid(row=1, column=1, padx=(10, 0), pady=5, sticky=tk.W)

        ttk.Label(fields_frame, text="Height:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.edit_height_var = tk.StringVar(value=self.edit_context['current_height'])
        height_entry = ttk.Entry(fields_frame, textvariable=self.edit_height_var, width=20)
        height_entry.grid(row=2, column=1, padx=(10, 0), pady=5, sticky=tk.W)

        ttk.Label(fields_frame, text="Max Expansion:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.edit_max_exp_var = tk.StringVar(value=self.edit_context['current_max_exp'])
        max_exp_entry = ttk.Entry(fields_frame, textvariable=self.edit_max_exp_var, width=20)
        max_exp_entry.grid(row=3, column=1, padx=(10, 0), pady=5, sticky=tk.W)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 10))

        ttk.Button(button_frame, text="Save Changes",
                   command=self.save_room_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel",
                   command=self.cancel_room_edit).pack(side=tk.LEFT, padx=5)

        name_entry.focus()
        name_entry.select_range(0, tk.END)

    def add_bulk_rooms(self):
        try:
            base_name = self.bulk_room_name_var.get().strip()
            quantity = int(self.bulk_room_quantity_var.get())
            width = int(self.bulk_room_width_var.get())
            height = int(self.bulk_room_height_var.get())
            max_exp = int(self.bulk_room_max_exp_var.get())

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

            existing_names = {self.rooms_tree.item(item)['text'] for item in self.rooms_tree.get_children()}

            new_room_names = []
            for i in range(1, quantity + 1):
                room_name = f"{base_name}{i}"
                if room_name in existing_names:
                    messagebox.showerror("Error", f"Room name '{room_name}' already exists")
                    return
                new_room_names.append(room_name)

            added_count = 0
            for room_name in new_room_names:
                try:
                    item = self.rooms_tree.insert("", "end", text=room_name)
                    self.rooms_tree.set(item, "Width", width)
                    self.rooms_tree.set(item, "Height", height)
                    self.rooms_tree.set(item, "Max Expansion", max_exp)
                    added_count += 1
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add room '{room_name}': {str(e)}")
                    break

            if added_count > 0:
                self.bulk_room_name_var.set("")
                self.bulk_room_quantity_var.set("")
                self.bulk_room_width_var.set("")
                self.bulk_room_height_var.set("")
                self.bulk_room_max_exp_var.set("")

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
            fontsize=base_font_size + 6,  # ✅ Increase font size
            fontweight='bold',  # ✅ Make it bold (optional)
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=bbox_alpha),
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
    root = tk.Tk()
    app = FloorPlanGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
