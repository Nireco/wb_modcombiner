
from header_operations import *
from header_common import *
import re

def generateID(caption, prefix = ""):
    return prefix + re.subn("[^\\w]", "", caption)[0].lower()

def displayerButton(item, (x, y, w, h), color):
    # (x,y,w,h) == (":column0", ":cur_y", c1-c0, unused)
    return [
                    (try_begin),
                        ] + item.conditions + [
                        (create_button_overlay, item.ap_id(), item.str_id(), 0),
                        (position_set_x, pos1, x),
                        (position_set_y, pos1, y),
                        (overlay_set_position, item.ap_id(), pos1),
                        (overlay_set_color, item.ap_id(), color),
#                        ["dynamic_set_color", item.ap_id()],
                    (else_try),
                        (create_text_overlay, reg0, item.str_id(), 0),
                        (position_set_x, pos1, x),
                        (position_set_y, pos1, y),
                        (overlay_set_position, reg0, pos1),
                        (overlay_set_color, reg0, 0x808080),
                    (try_end),
                    ]

def displayerLabel(item, (x,y,w,h), color):
    return [
                    (create_text_overlay, reg0, item.str_id(), 0),
                    (position_set_x, pos1, x),
                    (position_set_y, pos1, y),
                    (overlay_set_position, reg0, pos1),
                    (overlay_set_color, reg0, color),
                    (try_begin),
                        ] + item.conditions + [
                    (else_try),
                        (overlay_set_color, reg0, 0x808080),
                    (try_end),
                    ]

def displayerLabelInt(item, (x,y,w,h), color):
    return [
                    # caption
                    (create_text_overlay, reg0, item.str_id(), 0),
                    (position_set_x, pos1, x),
                    (position_set_y, pos1, y),
                    (overlay_set_position, reg0, pos1),
                    (overlay_set_color, reg0, color),
#                    ["dynamic_set_color", reg0],
                    # value
                    (create_number_box_overlay, item.ap_id(), item.limits[0], item.limits[1]),
                    (store_add, ":tmp_x", x, w),
                    (val_sub, ":tmp_x", 60),
                    (position_set_x, pos1, ":tmp_x"),
                    (position_set_y, pos1, ":cur_y"),
                    (overlay_set_position, item.ap_id(), pos1),
                    (try_begin),
                        # conditions for this being usable
                        ] + item.conditions + [
                    (else_try),
                        (overlay_set_color, reg0, 0x808080),
                    (try_end),
                    ] + item.load_value(":item_value") + [
                    (overlay_set_val, item.ap_id(), ":item_value"),
                    ]

def displayerCheckLabel(item, (x,y,w,h), color):
    return [
                    # caption
                    (create_text_overlay, reg0, item.str_id(), 0),
                    (store_add, ":tmp_x", x, 30),
                    (position_set_x, pos1, ":tmp_x"),
                    (position_set_y, pos1, y),
                    (overlay_set_position, reg0, pos1),
                    (overlay_set_color, reg0, color),
#                    ["dynamic_set_color", reg0],
                    # value
                    (create_check_box_overlay, item.ap_id(), "mesh_checkbox_off", "mesh_checkbox_on"),
                    (store_add, ":tmp_x", x, 7),
#                    (position_set_x, pos1, column[0] + 7),
                    (position_set_x, pos1, ":tmp_x"),
                    (store_add, ":tmp_y", y, 7),
                    (position_set_y, pos1, ":tmp_y"),
                    (overlay_set_position, item.ap_id(), pos1),
                    (try_begin),
                        # conditions for this being usable
                        ] + item.conditions + [
                    (else_try),
                        (overlay_set_color, reg0, 0x808080),
                    (try_end),
                    ] + item.load_value(":item_value") + [
                    (overlay_set_val, item.ap_id(), ":item_value"),
                    ]

def displayerLabelDropbox(item, (x,y,w,h), color):
    choicearr = []
    if len(item.choices) > 0:
        if isinstance(item.choices[0], str):
            # choices as a list of captions
            for ch in item.choices:
                choicearr.extend([
                    (str_store_string, s0, generateID(ch, "str_")),
                    (overlay_add_item, item.ap_id(), s0),
                ])
        elif isinstance(item.choices[0], (int, tuple)):
            # choices as a code which generates them
            choicearr.extend(item.choices)
    code = [
                    # caption
                    (create_text_overlay, reg0, item.str_id(), 0),
                    (position_set_x, pos1, x),
                    (position_set_y, pos1, y),
                    (overlay_set_position, reg0, pos1),
                    (overlay_set_color, reg0, color),
#                    ["dynamic_set_color", reg0],
                    # value
                    (create_combo_button_overlay, item.ap_id()),
                    (position_set_x, pos1, 800),
                    (position_set_y, pos1, 800),
                    (overlay_set_size, item.ap_id(), pos1),
                    (store_add, ":tmp_x", x, w),
                    (val_sub, ":tmp_x", 100), # dropbox is centered and I want to line the right side
                    (position_set_x, pos1, ":tmp_x"),
                    (position_set_y, pos1, y),
                    (overlay_set_position, item.ap_id(), pos1),
                    (try_begin),
                        # conditions for this being usable
                        ] + item.conditions + [
                    (else_try),
                        (overlay_set_color, reg0, 0x808080),
                        # disable, how?? todo, why??
                    (try_end),
                    ] + choicearr + [
                    ] + item.load_value(":item_value") + [
                    (overlay_set_val, item.ap_id(), ":item_value"),
                    ]
    return code

def displayerLabelString(item, (x,y,w,h), color):
    setinitial = []
    if hasattr(item, "stringreg"):
        setinitial = [(overlay_set_text, item.ap_id(), item.stringreg)]
    else:
        setinitial = [
                (str_clear, s0),
                (overlay_set_text, item.ap_id(), s0),
                ]
    code = [
                # caption
                (create_text_overlay, reg0, item.str_id(), 0),
                (position_set_x, pos1, x),
                (position_set_y, pos1, y),
                (overlay_set_position, reg0, pos1),
#                ["dynamic_set_color", reg0],
                (overlay_set_color, reg0, color),
                # value
                (create_simple_text_box_overlay, item.ap_id()),
#                    (position_set_x, pos1, column[1] - 100),
                (store_add, ":tmp_x", x, w),
                (val_sub, ":tmp_x", 200),
#                (store_sub, ":tmp_x", ":column1", 100),
                (position_set_x, pos1, ":tmp_x"),
                (position_set_y, pos1, y),
                (overlay_set_position, item.ap_id(), pos1),
                ] + setinitial + [
                ]
    return code

def displayerStringAlignRight(item, (x,y,w,h), color):
    setinitial = []
    if hasattr(item, "stringreg"):
        setinitial = [(overlay_set_text, item.ap_id(), item.stringreg)]
    else:
        setinitial = [
                (str_clear, s0),
                (overlay_set_text, item.ap_id(), s0),
                ]
    code = [
                # value
                (create_simple_text_box_overlay, item.ap_id()),
#                    (position_set_x, pos1, column[1] - 100),
                (store_add, ":tmp_x", x, w),
                (val_sub, ":tmp_x", 200),
#                (store_sub, ":tmp_x", ":column1", 100),
                (position_set_x, pos1, ":tmp_x"),
                (position_set_y, pos1, y),
                (overlay_set_position, item.ap_id(), pos1),
                ] + setinitial + [
                ]
    return code
