import bpy
import math
import bmesh
from mathutils import Vector, Matrix

# Clear existing objects
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Create new collection for the floor plan
    if "FloorPlan" not in bpy.data.collections:
        floor_plan_collection = bpy.data.collections.new("FloorPlan")
        bpy.context.scene.collection.children.link(floor_plan_collection)
    
    # Clear all materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
        
    # Set renderer to Cycles
    bpy.context.scene.render.engine = 'CYCLES'
    if hasattr(bpy.context.scene.cycles, 'device'):
        bpy.context.scene.cycles.device = 'GPU'

# Create materials - Fixed for compatibility with different Blender versions
def create_materials():
    # Wall material
    wall_mat = bpy.data.materials.new(name="WallMaterial")
    wall_mat.use_nodes = True
    wall_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1.0)
    
    # Floor material
    floor_mat = bpy.data.materials.new(name="FloorMaterial")
    floor_mat.use_nodes = True
    floor_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.75, 1.0)
    
    # Glass material for windows - simplified for compatibility
    glass_mat = bpy.data.materials.new(name="GlassMaterial")
    glass_mat.use_nodes = True
    glass_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.9, 1.0)
    glass_mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.2
    
    # Try to set IOR if available
    if "IOR" in glass_mat.node_tree.nodes["Principled BSDF"].inputs:
        glass_mat.node_tree.nodes["Principled BSDF"].inputs["IOR"].default_value = 1.45
    
    # Try to set Transmission if available
    if "Transmission" in glass_mat.node_tree.nodes["Principled BSDF"].inputs:
        glass_mat.node_tree.nodes["Principled BSDF"].inputs["Transmission"].default_value = 0.95
    elif "Transmission Weight" in glass_mat.node_tree.nodes["Principled BSDF"].inputs:
        glass_mat.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.95
    
    glass_mat.blend_method = 'BLEND'
    
    # Furniture materials
    wood_mat = bpy.data.materials.new(name="WoodMaterial")
    wood_mat.use_nodes = True
    wood_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.4, 0.2, 1.0)
    
    fabric_mat = bpy.data.materials.new(name="FabricMaterial")
    fabric_mat.use_nodes = True
    fabric_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.3, 0.5, 0.7, 1.0)
    
    kitchen_mat = bpy.data.materials.new(name="KitchenMaterial")
    kitchen_mat.use_nodes = True
    kitchen_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.2, 0.2, 1.0)
    
    return {
        "wall": wall_mat,
        "floor": floor_mat,
        "glass": glass_mat,
        "wood": wood_mat,
        "fabric": fabric_mat,
        "kitchen": kitchen_mat
    }

# Create floor
def create_floor(width, depth, materials):
    bpy.ops.mesh.primitive_plane_add(size=1)
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.scale.x = width
    floor.scale.y = depth
    floor.location.z = 0
    
    # Apply scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # Add material
    floor.data.materials.append(materials["floor"])
    
    # Move to collection
    move_to_collection(floor, "FloorPlan")
    
    return floor

# Create walls
def create_walls(width, depth, height, wall_thickness, materials):
    # Outer walls coordinates (clockwise from bottom left)
    wall_vertices = [
        (0, 0, 0),  # Bottom-left
        (width, 0, 0),  # Bottom-right
        (width, depth, 0),  # Top-right
        (0, depth, 0)  # Top-left
    ]
    
    walls = []
    
    # Create outer walls
    for i in range(4):
        start = wall_vertices[i]
        end = wall_vertices[(i+1) % 4]
        
        # Calculate wall dimensions and position
        wall_length = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
        wall_center_x = (start[0] + end[0]) / 2
        wall_center_y = (start[1] + end[1]) / 2
        
        # Create the wall mesh
        bpy.ops.mesh.primitive_cube_add(
            size=1, 
            location=(wall_center_x, wall_center_y, height/2)
        )
        wall = bpy.context.active_object
        wall.name = f"Wall_{i+1}"
        
        # Resize the wall
        if i % 2 == 0:  # Horizontal walls
            wall.scale.x = wall_length
            wall.scale.y = wall_thickness
        else:  # Vertical walls
            wall.scale.x = wall_thickness
            wall.scale.y = wall_length
        wall.scale.z = height
        
        # Apply material
        wall.data.materials.append(materials["wall"])
        
        # Apply transformations
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        
        # Move to collection
        move_to_collection(wall, "FloorPlan")
        
        walls.append(wall)
    
    return walls

# Create interior walls based on floor plan
def create_interior_walls(materials):
    interior_walls = [
        # Main interior walls - simplified approximation
        {"start": (6.0, 0.0), "end": (6.0, 9.0), "height": 2.4},  # Left to right dividing wall
        {"start": (9.0, 9.0), "end": (18.0, 9.0), "height": 2.4},  # Horizontal upper section
        {"start": (9.0, 0.0), "end": (9.0, 9.0), "height": 2.4},  # Middle vertical wall
        {"start": (12.0, 5.0), "end": (18.0, 5.0), "height": 2.4},  # Bathroom divider
        {"start": (15.0, 5.0), "end": (15.0, 9.0), "height": 2.4},  # Right rooms divider
    ]
    
    walls = []
    wall_thickness = 0.15
    
    for i, wall_data in enumerate(interior_walls):
        start = wall_data["start"]
        end = wall_data["end"]
        height = wall_data["height"]
        
        # Calculate wall dimensions and position
        wall_length = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
        wall_center_x = (start[0] + end[0]) / 2
        wall_center_y = (start[1] + end[1]) / 2
        
        # Create the wall mesh
        bpy.ops.mesh.primitive_cube_add(
            size=1, 
            location=(wall_center_x, wall_center_y, height/2)
        )
        wall = bpy.context.active_object
        wall.name = f"InteriorWall_{i+1}"
        
        # Determine if horizontal or vertical
        is_horizontal = abs(end[1] - start[1]) < abs(end[0] - start[0])
        
        # Resize the wall
        if is_horizontal:  # Horizontal walls
            wall.scale.x = wall_length
            wall.scale.y = wall_thickness
        else:  # Vertical walls
            wall.scale.x = wall_thickness
            wall.scale.y = wall_length
        wall.scale.z = height
        
        # Rotate if needed for angled walls
        if not is_horizontal and not abs(end[0] - start[0]) < 0.01:
            angle = math.atan2(end[1] - start[1], end[0] - start[0]) - math.pi/2
            wall.rotation_euler.z = angle
        
        # Apply material
        wall.data.materials.append(materials["wall"])
        
        # Apply transformations
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        
        # Move to collection
        move_to_collection(wall, "FloorPlan")
        
        walls.append(wall)
    
    return walls

# Create windows
def create_windows(materials):
    # Window positions based on floor plan - simplified
    windows = [
        {"pos": (1.5, 0.0), "width": 1.2, "height": 1.4},  # Front window left
        {"pos": (4.5, 0.0), "width": 1.2, "height": 1.4},  # Front window middle
        {"pos": (13.5, 0.0), "width": 1.2, "height": 1.4},  # Front window right
        {"pos": (16.5, 0.0), "width": 1.2, "height": 1.4},  # Front window far right
        {"pos": (0.0, 3.0), "width": 1.2, "height": 1.4, "rotate": True},  # Left side window
        {"pos": (18.0, 7.0), "width": 1.2, "height": 1.4, "rotate": True},  # Right side window
    ]
    
    window_objects = []
    wall_thickness = 0.15
    sill_height = 0.9
    
    for i, window_data in enumerate(windows):
        pos = window_data["pos"]
        width = window_data["width"]
        height = window_data["height"]
        rotate = window_data.get("rotate", False)
        
        # Create window frame (just a simplified cube with glass material)
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=(
                pos[0],
                pos[1] if not rotate else pos[1] + wall_thickness/2,
                sill_height + height/2
            )
        )
        window = bpy.context.active_object
        window.name = f"Window_{i+1}"
        
        if rotate:
            window.scale.x = wall_thickness
            window.scale.y = width
        else:
            window.scale.x = width
            window.scale.y = wall_thickness
        window.scale.z = height
        
        # Apply material
        window.data.materials.append(materials["glass"])
        
        # Apply transformations
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Move to collection
        move_to_collection(window, "FloorPlan")
        
        window_objects.append(window)
    
    return window_objects

# Create doors
def create_doors(materials):
    # Door positions - simplified
    doors = [
        {"pos": (9.0, 2.0), "width": 0.9, "height": 2.1, "rotate": False},  # Bedroom 1 door
        {"pos": (9.0, 6.0), "width": 0.9, "height": 2.1, "rotate": False},  # Bedroom 2 door
        {"pos": (12.0, 6.0), "width": 0.9, "height": 2.1, "rotate": False},  # Bathroom door
        {"pos": (12.0, 8.0), "width": 0.9, "height": 2.1, "rotate": True},   # Kitchen door
        {"pos": (15.0, 7.0), "width": 0.9, "height": 2.1, "rotate": False},  # Bedroom 3 door
        {"pos": (9.0, 0.5), "width": 1.2, "height": 2.1, "rotate": True},    # Front door
    ]
    
    door_objects = []
    
    for i, door_data in enumerate(doors):
        pos = door_data["pos"]
        width = door_data["width"]
        height = door_data["height"]
        rotate = door_data.get("rotate", False)
        
        # Create door frame (simplified)
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=(pos[0], pos[1], height/2)
        )
        door = bpy.context.active_object
        door.name = f"Door_{i+1}"
        
        if rotate:
            door.scale.x = width
            door.scale.y = 0.05
        else:
            door.scale.x = 0.05
            door.scale.y = width
        door.scale.z = height
        
        # Apply material
        door.data.materials.append(materials["wood"])
        
        # Apply transformations
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Move to collection
        move_to_collection(door, "FloorPlan")
        
        door_objects.append(door)
    
    return door_objects

# Create minimal furniture
def create_furniture(materials):
    furniture = []
    
    # Living room (TUPAK area)
    # Sofa
    bpy.ops.mesh.primitive_cube_add(size=1, location=(3.0, 6.0, 0.4))
    sofa = bpy.context.active_object
    sofa.name = "Sofa"
    sofa.scale = (2.5, 0.9, 0.8)
    sofa.data.materials.append(materials["fabric"])
    furniture.append(sofa)
    
    # Coffee table
    bpy.ops.mesh.primitive_cube_add(size=1, location=(5.0, 6.0, 0.25))
    coffee_table = bpy.context.active_object
    coffee_table.name = "CoffeeTable"
    coffee_table.scale = (1.2, 0.8, 0.5)
    coffee_table.data.materials.append(materials["wood"])
    furniture.append(coffee_table)
    
    # Dining table
    bpy.ops.mesh.primitive_cube_add(size=1, location=(5.0, 3.0, 0.4))
    dining_table = bpy.context.active_object
    dining_table.name = "DiningTable"
    dining_table.scale = (1.8, 1.0, 0.8)
    dining_table.data.materials.append(materials["wood"])
    furniture.append(dining_table)
    
    # Kitchen counters (KHH area)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(14.0, 8.0, 0.45))
    kitchen_counter = bpy.context.active_object
    kitchen_counter.name = "KitchenCounter"
    kitchen_counter.scale = (2.0, 0.6, 0.9)
    kitchen_counter.data.materials.append(materials["kitchen"])
    furniture.append(kitchen_counter)
    
    # Beds in bedrooms
    # Bedroom 1 (MH1)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(3.0, 2.0, 0.3))
    bed1 = bpy.context.active_object
    bed1.name = "Bed1"
    bed1.scale = (2.0, 1.4, 0.6)
    bed1.data.materials.append(materials["fabric"])
    furniture.append(bed1)
    
    # Bedroom 2 (MH2)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(3.0, 7.0, 0.3))
    bed2 = bpy.context.active_object
    bed2.name = "Bed2"
    bed2.scale = (2.0, 1.4, 0.6)
    bed2.data.materials.append(materials["fabric"])
    furniture.append(bed2)
    
    # Bedroom 3 (MH3)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(16.5, 7.0, 0.3))
    bed3 = bpy.context.active_object
    bed3.name = "Bed3"
    bed3.scale = (2.0, 1.4, 0.6)
    bed3.data.materials.append(materials["fabric"])
    furniture.append(bed3)
    
    # Bathroom elements (PESU)
    # Toilet
    bpy.ops.mesh.primitive_cube_add(size=1, location=(14.0, 3.5, 0.2))
    toilet = bpy.context.active_object
    toilet.name = "Toilet"
    toilet.scale = (0.6, 0.4, 0.4)
    toilet.data.materials.append(materials["wall"])
    furniture.append(toilet)
    
    # Shower
    bpy.ops.mesh.primitive_cube_add(size=1, location=(13.0, 2.0, 0.1))
    shower = bpy.context.active_object
    shower.name = "Shower"
    shower.scale = (1.0, 1.0, 0.2)
    shower.data.materials.append(materials["wall"])
    furniture.append(shower)
    
    # Apply transformations and move to collection
    for obj in furniture:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        move_to_collection(obj, "FloorPlan")
    
    return furniture

# Set up basic lighting
def create_lighting():
    # Create sun light
    bpy.ops.object.light_add(type='SUN', radius=1, location=(5, 5, 10))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 2.0
    
    # Create ambient light
    bpy.ops.object.light_add(type='AREA', radius=1, location=(9, 5, 5))
    ambient = bpy.context.active_object
    ambient.name = "AmbientLight"
    ambient.scale = (18, 9, 1)
    ambient.data.energy = 50.0
    
    # Move to collection
    move_to_collection(sun, "FloorPlan")
    move_to_collection(ambient, "FloorPlan")
    
    return [sun, ambient]

# Set up camera
def create_camera():
    bpy.ops.object.camera_add(location=(9, -10, 15), rotation=(math.radians(55), 0, 0))
    camera = bpy.context.active_object
    camera.name = "FloorPlanCamera"
    
    # Make this the active camera
    bpy.context.scene.camera = camera
    
    # Move to collection
    move_to_collection(camera, "FloorPlan")
    
    return camera

# Helper function to move objects to a collection
def move_to_collection(obj, collection_name):
    # Make sure the collection exists
    if collection_name not in bpy.data.collections:
        new_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(new_collection)
    
    # Link the object to the target collection
    if obj.name not in bpy.data.collections[collection_name].objects:
        bpy.data.collections[collection_name].objects.link(obj)
    
    # Unlink from the default collection
    if obj.name in bpy.context.collection.objects:
        bpy.context.collection.objects.unlink(obj)

# Main function to create the floor plan
def create_floor_plan():
    # Floor plan dimensions from the image (in meters)
    width = 18.0  # Approximate width
    depth = 9.0   # Approximate depth
    height = 2.4  # Standard ceiling height
    wall_thickness = 0.15  # Standard wall thickness
    
    # Clear existing scene and set up
    clear_scene()
    
    # Create materials
    materials = create_materials()
    
    # Create floor
    floor = create_floor(width, depth, materials)
    
    # Create outer walls
    outer_walls = create_walls(width, depth, height, wall_thickness, materials)
    
    # Create interior walls
    interior_walls = create_interior_walls(materials)
    
    # Create windows
    windows = create_windows(materials)
    
    # Create doors
    doors = create_doors(materials)
    
    # Create furniture
    furniture = create_furniture(materials)
    
    # Create lighting
    lights = create_lighting()
    
    # Set up camera
    camera = create_camera()
    
    # Set viewport shading
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
    
    print("Floor plan created successfully!")

# Run the script
if __name__ == "__main__":
    create_floor_plan()
