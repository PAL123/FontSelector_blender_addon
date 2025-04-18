import bpy
import os

from . import load_fonts as lf
from .addon_prefs import get_addon_preferences
from . import switch_font_operator as sw


def favorite_callback(self, context):
    
    debug = get_addon_preferences().debug
    
    font_props = context.window_manager.fontselector_properties
    
    if font_props.no_callback:
        if debug:
            print("FONTSELECTOR --- Favorite update function cancelled")
        return
    
    if debug:
        print(f"FONTSELECTOR --- Updating favorite : {self.name}")
    
    # Get favorite datas
    datas = lf.get_existing_favorite_datas()

    # Remove existing favorite entry
    idx = 0
    for font in datas["favorites"]:
        if font == self.name:
            datas["favorites"].pop(idx)
        idx += 1
        
    # Add entry
    if self.favorite:
        datas["favorites"].append(
            self.name,
        )

    # Write json
    path = lf.get_favorite_json_filepath()
    lf.write_json_file(datas, path)


class FONTSELECTOR_PR_single_font_properties(bpy.types.PropertyGroup):

    filepath: bpy.props.StringProperty(
        name = "Filepath",
        subtype = "FILE_PATH",
    )
    font_name: bpy.props.StringProperty(
        name = "Font Name",
    )


class FONTSELECTOR_PR_font_family_properties(bpy.types.PropertyGroup):

    favorite: bpy.props.BoolProperty(
        name = "Favorite",
        update = favorite_callback,
    )
    fonts : bpy.props.CollectionProperty(
        type=FONTSELECTOR_PR_single_font_properties,
    )
    multi_component: bpy.props.BoolProperty()


class FONTSELECTOR_PR_properties(bpy.types.PropertyGroup):

    font_families : bpy.props.CollectionProperty(
        type = FONTSELECTOR_PR_font_family_properties,
    )
    remove_existing_type_fonts : bpy.props.BoolProperty(
        name = "Remove Blender Type Fonts",
        description = "Remove blender type fonts (bold, italic, bold italic) slots on font change",
        default = True,
    )
    no_callback : bpy.props.BoolProperty()
    

def get_font_datablock(
    font,
    debug,
):
    
    new_font = None
    
    if debug:
        print(f"FONTSELECTOR --- Getting {font.filepath}")
    
    # Local
    try:
        # Existing datablock
        font_datablock = bpy.data.fonts[font.font_name]

        # Correct datablock
        if os.path.isfile(font_datablock.filepath):
            return font_datablock

        # Missing font file
        else:
            bpy.data.fonts.remove(font_datablock)
    
    except KeyError:
        if debug:
            print(f"FONTSELECTOR --- Importing : {font.font_name}")
        else:
            pass
        
    # Importing
    new_font = bpy.data.fonts.load(filepath=font.filepath)
    new_font.name = font.font_name
    
    # Prevent double users
    new_font.user_clear()
    
    return new_font


def clear_font_datas():
    for font in bpy.data.fonts:
        if font.name != "Bfont Regular"\
        and font.users == 0:
            bpy.data.fonts.remove(font)


def clear_obj_type_fonts(font_obj):

    # Get blender default font if available
    try:
        blank_font = bpy.data.fonts["Bfont Regular"]
    except KeyError:
        blank_font = None

    font_obj.font = blank_font
    font_obj.font_bold = blank_font
    font_obj.font_bold_italic = blank_font
    font_obj.font_italic = blank_font


def change_objects_font(
    target_font,
    self,
    context,
):

    font_props = context.window_manager.fontselector_properties

    # Prevent callback
    font_props.no_callback = True

    # Remove type fonts if needed
    if font_props.remove_existing_type_fonts:
        clear_obj_type_fonts(self.id_data)

    # Change active object font
    self.id_data.font = target_font

    # Properties to store font in case of index change
    family_name = font_props.font_families[self.family_index].name
    self.relink_family_name = family_name
    self.relink_type_name = self.family_types

    # Change selected objects
    for obj in context.selected_objects:
        if obj.type == "FONT":

            if obj.data == self.id_data:
                continue

            # Remove type fonts if needed
            if font_props.remove_existing_type_fonts:
                clear_obj_type_fonts(obj.data)

            obj.data.font = target_font

            props = obj.data.fontselector_object_properties
            props.family_index = self.family_index
            props.family_types = self.family_types

            props.relink_family_name = family_name
            props.relink_type_name = self.family_types


    font_props.no_callback = False
            

def change_strips_font(
    target_font,
    self,
    context,
):
    
    active_strip = context.active_strip

    font_props = context.window_manager.fontselector_properties

    # Prevent callback
    font_props.no_callback = True
    
    # Change active font
    active_strip.font = target_font

    # Properties to store font in case of index change
    family_name = font_props.font_families[self.family_index].name
    # active_strip.fontselector_object_properties.relink_family_name = family_name
    self.relink_family_name = family_name
    self.relink_type_name = self.family_types
    
    # Change selected objects
    for strip in context.selected_sequences:
        if strip.type == "TEXT":
            
            if strip == active_strip:
                continue
            
            strip.font = target_font
            
            props = strip.fontselector_object_properties
            props.family_index = self.family_index
            props.family_types = self.family_types

            props.relink_family_name = family_name
            props.relink_type_name = self.family_types

    font_props.no_callback = False


def family_type_update(self, context):

    debug = get_addon_preferences().debug

    font_props = context.window_manager.fontselector_properties

    if font_props.no_callback:
        if debug:
            print("FONTSELECTOR --- Update function cancelled")
        return

    if debug:
        print("FONTSELECTOR --- Update function")

    target_family = font_props.font_families[self.family_index]
    target_font_props = target_family.fonts[self.family_types]

    # Import font
    target_font = get_font_datablock(
        target_font_props,
        debug,
    )

    # Invalid font
    if target_font is None:
        if debug:
            print(f"FONTSELECTOR --- Update cancelled, unable to get font file : {target_font_props.name}")
        return

    # Find object or strip
    if isinstance(self.id_data, bpy.types.TextCurve):

        change_objects_font(
            target_font,
            self,
            context,
        )

    else:

        change_strips_font(
            target_font,
            self,
            context,
        )

    # Clear old fonts
    clear_font_datas()


def family_selection_update(self, context):

    debug = get_addon_preferences().debug

    font_props = context.window_manager.fontselector_properties

    if font_props.no_callback\
    or self.family_index == -1:
        if debug:
            print("FONTSELECTOR --- Update function cancelled")
        return

    if debug:
        print("FONTSELECTOR --- Update function")

    # Set first available type
    first_type = sw.get_enum_values(
                    self,
                    "family_types",
                )[0]

    self.family_types = first_type
    

def family_type_callback(self, context):
    items = []

    font_props = context.window_manager.fontselector_properties

    target_family_props = font_props.font_families[self.family_index]

    for font in target_family_props.fonts:
        items.append(
            (font.name, font.name, ""),
        )

    return items


class FONTSELECTOR_PR_object_properties(bpy.types.PropertyGroup):

    # Search
    font_search: bpy.props.StringProperty(
        options = {"TEXTEDIT_UPDATE"},
    )

    # Relink Font
    relink_family_name : bpy.props.StringProperty()
    relink_type_name : bpy.props.StringProperty()

    # Families
    family_index : bpy.props.IntProperty(
        default = -1,
        update = family_selection_update,
    )
    family_name : bpy.props.StringProperty()
    family_types : bpy.props.EnumProperty(
        name = "Types",
        items = family_type_callback,
        update = family_type_update,
    )
    
    # Display
    show_favorite : bpy.props.BoolProperty(
        name = "Show Favorites",
        description = "Show Favorites icon",
        default=True,
    )
    show_multi_component : bpy.props.BoolProperty(
        name = "Show Multi Component Families",
        description = "Show Multi Component Families icon",
        default=True,
    )
    
    # Filters
    favorite_filter : bpy.props.BoolProperty(
        name = "Favorites Filter",
        description = "Show only Favorites",
    )
    invert_filter : bpy.props.BoolProperty(
        name = "Invert Filters",
        description = "Invert Filters",
    )
    
    # Search filters
    search_filepath : bpy.props.BoolProperty(
        name = "Search Font Filepath",
        description = "Search individual fonts filepath",
    )
    search_font_names: bpy.props.BoolProperty(
        name = "Search Font Names",
        description = "Search individual fonts names",
    )


### REGISTER ---
def register():
    bpy.utils.register_class(FONTSELECTOR_PR_single_font_properties)
    bpy.utils.register_class(FONTSELECTOR_PR_font_family_properties)
    bpy.utils.register_class(FONTSELECTOR_PR_properties)
    bpy.utils.register_class(FONTSELECTOR_PR_object_properties)
    
    bpy.types.WindowManager.fontselector_properties = \
        bpy.props.PointerProperty(
            type = FONTSELECTOR_PR_properties,
            name="Font Selector Properties",
        )
    bpy.types.TextCurve.fontselector_object_properties = \
        bpy.props.PointerProperty(
            type = FONTSELECTOR_PR_object_properties,
            name="Font Selector Properties",
        )
    bpy.types.TextStrip.fontselector_object_properties = \
        bpy.props.PointerProperty(
            type = FONTSELECTOR_PR_object_properties,
            name="Font Selector Properties",
        )

def unregister():
    bpy.utils.unregister_class(FONTSELECTOR_PR_single_font_properties)
    bpy.utils.unregister_class(FONTSELECTOR_PR_font_family_properties)
    bpy.utils.unregister_class(FONTSELECTOR_PR_properties)
    bpy.utils.unregister_class(FONTSELECTOR_PR_object_properties)
    
    del bpy.types.WindowManager.fontselector_properties
    del bpy.types.TextCurve.fontselector_object_properties
    del bpy.types.TextStrip.fontselector_object_properties
