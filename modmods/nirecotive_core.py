# category: Nirecotive Core 

from modmod import ModMod

from header_operations import *
from header_common import *

import header_operations
import logging
import re
import copy
import os
from menuitemdisplayers import *
import version_number
from version_number import *

################################################################################
# lists which accumulate Items
all_items = []
accum_items = []


################################################################################
# some channel constants, mainly from N2
mp_nir_server                                   = 120
mp_nir_client                                   = 121
multiplayer_event_nir_store_string              = 122
multiplayer_event_nir_store_string_server       = 123
multiplayer_event_nir_store_string_server_weak  = 124
mp_nir_send_colored_message                     = 125
#mp_event_nirext_send_string                     = 0 # what does this even do??
mp_event_debug_static_string                    = 0
mp_copy_string                                  = 399


################################################################################
################################################################################
# Check-generators and other useful code shorthands
################################################################################
################################################################################
def checkAdmin(player, minor=None, ornext=False):
    '''
    Returns code which checks if the given player is an admin. If ornext is
    True, will use this_or_next. With this_or_next you should have some other
    condition on the next line (Do not use function generated check or
    call_script for that).

    Planned:
        minor:
            A list of strings defining different minor admin powers. If the
            player is given minor admin powers in one of those categories, this
            check will succeed.
    '''
    if ornext:
        return [
                    (this_or_next|player_is_admin, player),
                    ]
    else:
        return [
                    (player_is_admin, player),
                    ]

def checkOutOfMenuScript():
    '''
    The test will fail if the user is in any menu marked as a Presentation by
    this module.
    '''
    content = []
    for item in all_items:
        if isinstance(item, Presentation):
            content.append((neg|is_presentation_active, item.pres_id()))
    return [
                    ("cf_client_check_not_in_menu", [
                        ] + content + [
                    ]),
                ]

def sendToAll(receivers, code):
    '''
    Will execute the given code for all active players which match the receiver
    category.

    ":player"
        loop variable over all players
    '''
    if receivers == "all":
        return [
                    (get_max_players, ":num_players"),
                    (try_for_range, ":player", 1, ":num_players"),
                        (player_is_active, ":player"),
                        ] + code + [
                    (try_end),
                    ]
    elif receivers == "nirecotive":
        return [
                    (get_max_players, ":num_players"),
                    (try_for_range, ":player", 1, ":num_players"),
                        (player_is_active, ":player"),
                        ] + checkPlayerHasThisMod(":player") + [
#                        (player_get_slot, ":nirversion", ":player", 52),
                        # if the client has told to send this information TODO
                        ] + code + [
                    (try_end),
                    ]
    elif receivers == "sender":
        return [
                    (try_begin),
                        (assign, ":player", ":player_no"),
                        (player_is_active, ":player"),
                        ] + code + [
                    (try_end),
                    ]
    elif receivers == "admin":
        return [
                    (get_max_players, ":num_players"),
                    (try_for_range, ":player", 1, ":num_players"),
                        (player_is_active, ":player"),
                        ] + checkAdmin(":player") + [
                        ] + code + [
                    (try_end),
                    ]
    elif receivers == "none":
        return []
    else:
        raise Exception("Unknown receiver: %s" % receivers)
    return []

def getActionCodeFor(items):
    code = []
    # this piece is caller's responsibility
#    code.extend([
#                (try_begin),
#                    (eq, 1,2), # for easier looping
#                ])
    for a in items:
        if isinstance(a, Item):
            if hasattr(a, "actionHandler"):
                code.extend([
                (else_try),
                    (eq, ":object", a.ap_id()),
                    ] + a.actionHandler + [
                ])
        elif isinstance(a, list):
            code.extend([
                (else_try),
                    (eq, ":object", a[0].ap_id()),
                    ] + a[0].actionHandler + [
                ])
        else:
            code.extend([
                (else_try),
                    (eq, ":object", a.ap_id()),
                    ] + a.getAction() + [
                ])
    # this piece is caller's responsibility
#    code.extend([
#                (try_end),
#                ])
    return code

################################################################################
################################################################################
# Different kind of Items
################################################################################
################################################################################
class HelperItem:
    '''
    Used to create 'hr', 'indent' and 'dedent' for Menus
    '''
    def __init__(self, string):
        self.string = string
        accum_items.append(self)


class clientItem:
    '''
    Marks item to be a client item
    '''
    pass



class Item:
    def __init__(self, vid):
        self.vid = vid
        if not isinstance(vid, str):
            print "Error, why is vid not string? %s" % str(vid)
        # self.strings = []
        # self.actionHandler
        # self.clientHandler        # ":player_no", ":val1", ":val2", ":val3"
        # self.serverHandler        # ":player_no", ":val1", ":val2", ":val3"
        # self.sendInitialHandler   # ":player"

        # self.caption
        # self.choices
        # self.limits
        self.vartype = 'unknown'    # this is for nirecotive default setter
        #   'int' for boolean and int
        #   'string' for string
        #   'dropbox' for dropbox
        #   'channel' for ignoring initialization possibility
        #   'action' also for ignoring initialization
        # for being able to override where the information gets stored (arrays)
        self.loader = lambda x, target : [(assign, target, x.var_id())]
        self.saver = lambda x, value :  [(assign, x.var_id(), value)]
        #                           # from some other mod.
        all_items.append(self)
        accum_items.append(self)

    def pres_id(self):
        return "prsnt_" + self.vid
    def ap_id(self):
        return "$g_pres_" + self.vid
    def var_id(self):
        '''
        Consider using loader and saver functions through self.load_value and
        self.save_value instead of directly using var_id.
        '''
        return "$g_" + self.vid
    def str_id(self):
        return "str_" + self.vid
    def trp_id(self):
        return "trp_" + self.vid
    def get_channel(self, mode="server"):
        '''
        need to have server and client separately for compability with N2.
        '''
        if not hasattr(self, "channel"):
            raise Exception("Trying to get channel from Item without one")
        channel = self.channel
        if isinstance(channel, (list, tuple)):
            # you shouldn't give channel as list outside this file to not mess
            # with other mods' channel space.
            if mode == "server" or len(channel) < 2:
                channel = channel[0]
            else:
                channel = channel[1]
            return channel
        if channel > 100000:
            raise Exception("Trying to use channel above 100000, you are getting out of allocated channels")
        the_mod = version_number.this_mod
        if the_mod in ["Nirecotive", "Custom Nirecotive"]:
            pass
        else:
            channel += major_values[the_mod] * 100000
        return channel
    def load_value(self, target):
        return self.loader(self, target)
    def save_value(self, value):
        return self.saver(self, value)
    # for using, var_id()
    # for displaying, getDisplay needed
    #   for displaying, caption needed?
    #   for displaying, ap_id()
    #   for displaying, str_id()
    # fancifying display, conditions needed
    # for the displaying thing to do something, actionHandler needed
    # for server sending serverHandler needed
    # for client sending clientHandler needed
    #   for serverHandler and clientHandler, channel needed



class constString(Item):
    '''
    Defines a constant string
    '''
    def __init__(self, caption, vid=None):
        Item.__init__(self, (vid or generateID(caption)))
        self.vartype = 'none'
        self.caption = caption
        self.strings = [(self.vid, self.caption)]
class boolItem(Item):
    '''
    Item to store an boolean value locally
    '''
    def __init__(self, vid):
        Item.__init__(self, vid)
        self.vartype = 'int'
class intItem(Item):
    '''
    Item to store an integer value locally
    '''
    def __init__(self, limits, vid):
        Item.__init__(self, vid)
        self.limits = limits
        self.vartype = 'int'
class channelItem(Item):
    '''
    An item which has a reserved channel for communicating with the server
    '''
    def __init__(self, vid, channel):
        Item.__init__(self, vid)
        self.channel = channel
        self.vartype = 'channel'
    def buildActionHandler(self, values):
        '''
        Function to build an action handler, which will will send the given
        values on this channel, when this item's action is triggered (needs
        displayer too).
        '''
        self.actionHandler = [
                    (multiplayer_send_2_int_to_server, mp_nir_server, self.get_channel("server")) + values,
                    ]
class actionItem(Item):
    '''
    Marks the item to be an action
    '''
    def __init__(self, vid):
        Item.__init__(self, vid)
        self.vartype = 'action'

class syncedIntItem(Item):
    '''
    A synchronised integer item with no displayer defined.
    '''
    def __init__(self, channel, limits, vid):
        '''
        channel
            The channel to communicate on
        limits
            A two item list with the minimum and the maximum value of this item
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        '''
        Item.__init__(self, vid)
        self.vartype = 'int'
        self.channel = channel
        self.vid = vid
        self.limits = limits
        self.serverHandler = [
                    (player_is_admin, ":player_no"), # TODO: change to checkAdmin()
                    (is_between, ":val1", self.limits[0], self.limits[1]),
                    ] + self.save_value(":val1") + [
#                    (assign, self.var_id(), ":val1"),
                    ] + sendToAll('nirecotive', [
                        (multiplayer_send_2_int_to_player, ":player", mp_nir_client, self.get_channel("client"), ":val1"),
                        (str_store_player_username, s0, ":player"),
#                        (display_message, "@Sent to {s0}"),
                        ]) + [
                    ]
        self.clientHandler = [
                    ] + self.save_value(":val1") + [
#                    (display_message, "@got a value"),
#                    (assign, self.var_id(), ":val1"),
                    ]
        self.sendInitialHandler = [
                    ] + self.load_value(":item_value") + [
                    (multiplayer_send_2_int_to_player, ":player", mp_nir_client, self.get_channel("client"), ":item_value"),
                    ]

################################################################################
# menu button
#
class buttonItem(actionItem):
    '''
    A button item
    '''
    def __init__(self, caption, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            If these conditions are not met, this item will be showed as gray.
        '''
        actionItem.__init__(self, (vid or generateID(caption)))
        self.caption = caption
        self.conditions = conditions
        self.strings = [(self.vid, caption)]
        self.displayer = displayerButton
class serverButtonItem(buttonItem, channelItem):
    '''
    A button item which will send the assigned channel to the server. Use
    buildActionHandler if you want to send some information on that channel.
    '''
    def __init__(self, caption, channel, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        channel
            The channel to communicate on
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            If these conditions are not met, this item will be showed as gray.
        '''
        buttonItem.__init__(self, caption, vid, conditions)
        channelItem.__init__(self, self.vid, channel)
        self.caption = caption
        self.strings = [(self.vid, caption)]
        self.buildActionHandler(())
    def buildActionHandler(self, values):
        self.actionHandler = [
                    (multiplayer_send_2_int_to_server, mp_nir_server, self.get_channel("server")) + values,
                    ]

class labelItem(actionItem):
    '''
    Label item
    '''
    def __init__(self, caption, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            If these conditions are not met, this item will be showed as gray.
        '''
        actionItem.__init__(self, (vid or generateID(caption)))
        self.caption = caption
        self.conditions = conditions
        self.strings = [(self.vid, caption)]
        self.displayer = displayerLabel



################################################################################
# int
#
class intAdminItem(syncedIntItem):
    '''
    Integer box which will be synced with server
    '''
    def __init__(self, caption, channel, limits, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        channel
            The channel to communicate on
        limits
            A two item list with the minimum and the maximum value of this item
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            Conditions which must be met for this item to have effect. It can
            still be set to some value.
        '''
        syncedIntItem.__init__(self, channel, limits, (vid or generateID(caption)))
        self.caption = caption
        self.strings = [(self.vid, caption)]
        self.conditions = conditions
        self.actionHandler = [
                    (multiplayer_send_2_int_to_server, mp_nir_server, self.get_channel("server"), ":value"),
                    ]
        self.displayer = displayerLabelInt
class clientIntItem(intItem):
    '''
    Integer item which will be stored locally.
    '''
    def __init__(self, caption, limits, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        limits
            A two item list with the minimum and the maximum value of this item
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            Conditions which must be met for this item to have effect. It can
            still be set to some value.
        '''
        intItem.__init__(self, limits, (vid or generateID(caption)))
        self.limits = limits
        self.caption = caption
        self.strings = [(self.vid, caption)]
        self.conditions = conditions
        self.actionHandler = [
#                    (assign, self.var_id(), ":value"),
                    ] + self.save_value(":value") + [
                    ]
        self.displayer = displayerLabelInt


################################################################################
# boolean
#
class boolAdminItem(syncedIntItem):
    '''
    Check box, which value will be synced with server.
    '''
    def __init__(self, caption, channel, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        channel
            The channel to communicate on
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            Conditions which must be met for this item to have effect. It can
            still be set to some value.
        '''
        syncedIntItem.__init__(self, channel, [0, 2], (vid or generateID(caption)))
        self.caption = caption
        self.strings = [(self.vid, caption)]
        self.conditions = conditions
        self.actionHandler = [
                    (multiplayer_send_2_int_to_server, mp_nir_server, self.get_channel("server"), ":value"),
                    ]
        self.displayer = displayerCheckLabel
class clientBoolItem(boolItem):
    '''
    Check box, which value will be stored locally.
    '''
    def __init__(self, caption, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            Conditions which must be met for this item to have effect. It can
            still be set to some value.
        '''
        boolItem.__init__(self, (vid or generateID(caption)))
        self.caption = caption
        self.strings = [(self.vid, caption)]
        self.conditions = conditions
        self.actionHandler = [
#                    (assign, self.var_id(), ":value"),
                    ] + self.save_value(":value") + [
                    ]
        self.displayer = displayerCheckLabel


################################################################################
# dropbox
#
        
class dropboxAdminItem(syncedIntItem):
    '''
    Dropbox element, which value will be synced with the server.
    '''
    def __init__(self, caption, channel, choices, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        channel
            The channel to communicate on
        choices
            A list of different choice captions in the dropbox.
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            Conditions which must be met for this item to have effect. It can
            still be set to some value.
        '''
        syncedIntItem.__init__(self, channel, [0, len(choices)], (vid or generateID(caption)))
        self.vartype = 'dropbox'
        self.caption = caption
        self.choices = choices
        self.conditions = conditions
        self.actionHandler = [
                    (multiplayer_send_2_int_to_server, mp_nir_server, self.get_channel("server"), ":value"),
                    ]
        self.displayer = displayerLabelDropbox
        self.strings = [(self.vid, caption)]
        if len(choices) > 0 and isinstance(choices[0], (int, tuple)):
            self.limits = [0, 1000]
            self.vartype = 'onlyzeroinit'
        elif len(choices) > 0 and isinstance(choices[0], str):
            self.strings.extend([(generateID(ch), ch) for ch in choices])
    def get_choice_idx(self, ch):
        '''
        Returns the index value of a choice when given the caption string of
        that choice.
        '''
        if len(choices) > 0 and isinstance(choices[0], (int, tuple)):
            raise Exception("Trying to get a choice index from generated choices")
        if not ch in self.choices:
            raise Exception("no such choice: %s" % str(ch))
        return self.choices.index(ch)
class clientDropboxItem(Item):
    '''
    Dropbox element, which value will be stored locally.
    '''
    def __init__(self, caption, choices, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        choices
            A list of different choice captions in the dropbox.
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            Conditions which must be met for this item to have effect. It can
            still be set to some value.
        '''
        Item.__init__(self, (vid or generateID(caption)))
        self.vartype = 'dropbox'
        self.limits = [0, len(choices)]
        self.caption = caption
        self.choices = choices
        self.conditions = conditions
        self.actionHandler = [
#                    (assign, self.var_id(), ":value"),
                    ] + self.save_value(":value") + [
                    ]
        self.displayer = displayerLabelDropbox
        self.strings = [(self.vid, caption)]
        if len(choices) > 0 and isinstance(choices[0], (int, tuple)):
            self.limits = [0, 1000]
            self.vartype = 'donotinitialize'
        elif len(choices) > 0 and isinstance(choices[0], str):
            self.strings.extend([(generateID(ch), ch) for ch in choices])
    def get_choice_idx(self, ch):
        if len(choices) > 0 and isinstance(choices[0], (int, tuple)):
            raise Exception("Trying to get a choice index from generated choices")
        if not ch in self.choices:
            raise Exception("no such choice: %s" % str(ch))
        return self.choices.index(ch)


################################################################################
# string
#
class clientStringItem(Item):
    '''
    String item, which will be stored locally.
    '''
    def __init__(self, caption, stringreg, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        stringreg
            String register which is reserved for this string item.
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            Conditions which must be met for this item to have effect. It can
            still be set to some value.
        '''
        Item.__init__(self, (vid or generateID(caption)))
        self.vartype = 'string'
        if stringreg != None:
            self.stringreg = stringreg
        self.caption = caption
        self.strings = [(self.vid, caption),
                        (self.vid+"_default", " ")]
        self.conditions = conditions
        if self.stringreg:
            self.actionHandler = [
                    (str_store_string_reg, self.stringreg, s0),
                    ]
        #
        self.displayer = displayerLabelString

class stringAdminItem(clientStringItem):
    '''
    String item which will be synced to the server and all other admins.
    '''
    def __init__(self, caption, stringreg, vid=None, conditions=[]):
        '''
        caption
            A text caption shown on the left of the dropbox.
        stringreg
            String register which is reserved for this string item.
        vid
            An identifier, if you don't want to let the program autogenerate
            it from the caption.
        conditions
            Conditions which must be met for this item to have effect. It can
            still be set to some value.
        '''
        clientStringItem.__init__(self, caption, stringreg, vid, conditions)
        self.actionHandler = [
                    (multiplayer_send_string_to_server, multiplayer_event_nir_store_string_server, s0),
                    (multiplayer_send_4_int_to_server, mp_nir_server, mp_copy_string, self.stringreg, s52, 1)
                    ]
        self.sendInitialHandler = [
                    (try_begin),
                        ] + checkAdmin(":player") + [
                        (multiplayer_send_string_to_player, ":player", multiplayer_event_nir_store_string, self.stringreg),
                        (multiplayer_send_4_int_to_player, ":player", mp_nir_client, mp_copy_string, self.stringreg, s52, 0),
                    (try_end),
                    ]




class extendChannelItem(Item):
    def __init__(self, vid, other, side, content):
        '''
        vid
            an identifier
        other
            an item with channel attribute to add extra processing for that
            channel
        side
            "server" or "client" depending on which of them you want to add
            processing to.
        content
            code content to execute
        '''
        Item.__init__(self, vid)
        self.vartype = 'channel'
        self.content = content
        self.side = side
        self.other = other



def generateID(caption, prefix = ""):
    '''
    Generates a valid identifier from the given caption by removing all
    non-alphanumeric characters and changing the alphabets to lowercase. If
    prefix is given, that will be placed to prefix the identifier.
    '''
    return prefix + re.subn("[^\\w]", "", caption)[0].lower()


################################################################################
################################################################################
# Slot
################################################################################
################################################################################

class Slot:
    '''
    container
        the data type to hold this slot. For example, "player", "troop". And
        then you have player_get_slot and troop_get_slot.
    '''
    def __init__(self, 
                container, 
                slotnumber # could be autodetected, if we had start amounts for types
                ):
        self.container = container
        self.slotnumber = slotnumber

    def slot(self):
        return self.slotnumber

################################################################################
################################################################################
# Menus and Presentation
################################################################################
################################################################################

def createMenuTabGroup(menus):
    '''
    For binding the given menus as a tab-group giving them tabs to move between
    each other
    '''
    for menu in menus:
        if isinstance(menu, Menu):
            menu.tabgroup = menus

def getAccumItems():
    '''
    Returns all the Items which have accumulated after last creation of Menu
    object.
    '''
    global accum_items
    ret = accum_items
    accum_items = []
    return ret

class Presentation(Item):
    def __init__(self, caption, vid=None):
        Item.__init__(self, (vid or generateID(caption)))
        self.caption = caption
        self.vartype = 'presentation'

class Menu(Presentation):
    '''
    A menu. Use addAction and bulkAddAction to add actions: Item objects

    Adding HelperItem("hr") will generate extra space
    HI("indent") and HI("dedent") will control indentation.
    '''
    def __init__(self, caption, layout="ingame_menu", vid=None, conditions=[]):
        Presentation.__init__(self, caption, (vid or "presentation_" + generateID(caption)))
        global accum_items
        self.caption = caption
        self.actions = []
#        self.vid = "presentation_" + generateID(self.caption)
        self.tabgroup = []
        self.layoutmode = layout
        self.conditions = conditions

        accum_items = []
        self.strings = [(self.vid, self.caption)]

    def tab_var_id(self):
        return "$g_" + self.vid + "_tabvar"
    def bulkAddAction(self, actions):
        for a in actions:
            self.addAction(a)
    def addAction(self, action, displayer=None):
        if isinstance(action, HelperItem):
            self.actions.append(action.string)
        else:
            if displayer:
                self.actions.append([action, displayer])
            else:
                self.actions.append(action)
    def getActionObjects(self):
        return filter(lambda x: not isinstance(x, str), self.actions)

    def getTotalHeight(self, increment):
        total_height = 0
        for a in self.actions:
            opts = {}
            if isinstance(a, list):
                opts = a[1]
                a = a[0]
            if isinstance(a, str):
                if a == "hr":
                    total_height += increment / 2
            else:
                if (hasattr(a, "inline") and a.inline == True) or \
                            ("inline" in opts and opts["inline"]):
                    pass
                else:
                    total_height += increment
        return total_height

    def getPresentation(self):
        if self.layoutmode == "admin_panel":
            return self.getAsAdminPanel()
        elif self.layoutmode == "ingame_menu":
            return self.getAsIngameMenu()
        elif self.layoutmode == "wide_ingame":
            return self.getAsWideIngameMenu()
        else:
            return []

    def getActionDisplayCode(self, columns, increment, color=0x000000):
        code = [
                        (assign, ":column0", columns[0]),
#                        (assign, ":column1", columns[1]), # deprecated
                        (assign, ":area_width", columns[1] - columns[0]),
                        ]
        for a in self.actions:
            if hasattr(a, "inline") and a.inline == True:
                code.append((val_add, ":cur_y", increment))
            if isinstance(a, str):
                if a == "indent":
                    columns[0] += 30
                    code.append((val_add, ":column0", 30),)
                    code.append((val_sub, ":area_width", 30),)
                elif a == "dedent":
                    columns[0] -= 30
                    code.append((val_sub, ":column0", 30),)
                    code.append((val_add, ":area_width", 30),)
                elif a == "hr":
                    code.append((val_sub, ":cur_y", increment / 2))
            elif isinstance(a, list):
                opts = a[1]
                if "displayer" in opts:
                    newcode = opts["displayer"](a[0], (":column0", ":cur_y", ":area_width", -1), color)
                else:
                    newcode = a[0].displayer(a[0], (":column0", ":cur_y", ":area_width", -1), color)
                code.extend(newcode)
                code.append((val_sub, ":cur_y", increment)),
            elif isinstance(a, Item) and hasattr(a, 'displayer'):
                newcode = a.displayer(a, (":column0", ":cur_y", ":area_width", -1), color)
                code.extend(newcode)
                code.append((val_sub, ":cur_y", increment)),
        return code

    def getAsIngameMenu(self):
        columns = [30, 420]
        yadd = 28
        total_height = self.getTotalHeight(yadd) + 10
        background = "mesh_mp_ingame_menu"
        menupos = [250, 80, 1000, 1000] # was too high with 1000
        contpos = [285, 125,  425,  500] # mixed this with menupos...
        # generate code for caption
        captioncode = [
                    (create_text_overlay, reg0, self.str_id(), 0),
                    (overlay_set_color, reg0, 0xFFFFFF),
                    (position_set_x, pos1, 0),
                    (position_set_y, pos1, ":cur_y"),
                    (overlay_set_position, reg0, pos1),
                    (val_sub, ":cur_y", yadd),
                    ]
        tab_positioning = {
                "global_background":"mesh_mp_ingame_menu",
                "bgx":35,
                "bgy":80,
                "bgw":400,
                "bgh":1000,
                "startx":135,
                "starty":617,
                "deltax":0,
                "deltay":-30,
                }
        tab_code, tab_act = self.getTabCode(tab_positioning)
        # count total height
        return self.getGenericDisplay(columns, yadd, background, menupos, contpos, captioncode,
                    [tab_code, tab_act], color=0xFFFFFF)

    def getAsWideIngameMenu(self):
        columns = [30, 570]
        yadd = 28
        total_height = self.getTotalHeight(yadd) + 10
        background = "mesh_mp_ingame_menu"
        menupos = [250, 80, 1400, 1000] # was too high with 1000
        contpos = [285, 125,  600,  500] # mixed this with menupos...
        # generate code for caption
        captioncode = [
                    (create_text_overlay, reg0, self.str_id(), 0),
                    (overlay_set_color, reg0, 0xFFFFFF),
                    (position_set_x, pos1, 0),
                    (position_set_y, pos1, ":cur_y"),
                    (overlay_set_position, reg0, pos1),
                    (val_sub, ":cur_y", yadd),
                    ]
        tab_positioning = {
                "global_background":"mesh_mp_ingame_menu",
                "bgx":35,
                "bgy":80,
                "bgw":400,
                "bgh":1000,
                "startx":135,
                "starty":617,
                "deltax":0,
                "deltay":-30,
                }
        tab_code, tab_act = self.getTabCode(tab_positioning)
        # count total height
        return self.getGenericDisplay(columns, yadd, background, menupos, contpos, captioncode,
                    [tab_code, tab_act], color=0xFFFFFF)

    def getAsAdminPanel(self):
        columns = [0, 490] # second value varies...
        # count total height
        yadd = 28
        # create action display code for embedding
        # get admin panel header definitions
        background = "mesh_mp_ui_host_main"
        menupos = [-1, -1, 1002, 1002]
        contpos = [59, 50,  690,  520]
        # no caption
        captioncode = []
        # extra buttons
        extrabuttons = [
                    (create_button_overlay, "$g_presentation_obj_back", "str_back", tf_center_justify),
                    (position_set_x, pos1, 825),
                    (position_set_y, pos1, 50),
                    (overlay_set_position, "$g_presentation_obj_back", pos1),
                    (position_set_x, pos1, 1500),
                    (position_set_y, pos1, 1500),
                    (overlay_set_size, "$g_presentation_obj_back", pos1),
                    ]
        extra_actions = [
                    (else_try),
                        (eq, ":object", "$g_presentation_obj_back"),
                        (presentation_set_duration, 0),
                    ]
        tab_positioning = {
                "background":"mesh_mp_ui_welcome_panel",
                "tabwidth":277,
                "tabheight":150,
                "startx":0,
                "starty":572,
                "deltax":166,
                "deltay":0,
                "perline":6,
                "delta2x":50,
                "delta2y":30,
                }
        tab_code, tab_act = self.getTabCode(tab_positioning)
        return self.getGenericDisplay(columns, yadd, background, menupos, contpos, captioncode, 
                extra=[extrabuttons + tab_code, extra_actions + tab_act], color=0x000000)
    def getTabCode(self, tab_positioning, impose=None):
        code = []
        actcode = []
        tp = tab_positioning
        i = 0
        x = tp["startx"]
        y = tp["starty"]
        sx = x
        sy = y
        if "global_background" in tp:
            code.extend([
                (create_mesh_overlay, reg0, tp["global_background"]),
                (position_set_x, pos1, tp["bgw"]),
                (position_set_y, pos1, tp["bgh"]),
                (overlay_set_size, reg0, pos1),
                (position_set_x, pos1, tp["bgx"]),
                (position_set_y, pos1, tp["bgy"]),
                (overlay_set_position, reg0, pos1),
                (overlay_set_color, reg0, 0xFFBBBBBB),
                ])
            
        for menu in self.tabgroup:
            caption = ""
            prsnt = ""
            butvar = ""
            strname = ""
            isthis = False
            color = 0xFFFFFF
            conditions = []
            if isinstance(menu, Menu):
                caption = menu.caption
                prsnt = menu.pres_id()
                butvar = menu.tab_var_id()
                strname = menu.str_id()
                conditions = menu.conditions
                if (not impose and menu == self) or (menu == impose):
                    color = 0xFFFF00
                    isthis = True
                else:
                    color = 0xFFFFFF
            elif isinstance(menu, (list, tuple)):
                caption, prsnt = menu
                butvar = generateID(caption, "$g_tabvar_")
                strname = generateID(caption, "str_")
                if impose and prsnt == impose:
                    color = 0xFFFF00
                    isthis = True
            if "background" in tp.keys():
                code.extend([
                (create_mesh_overlay, reg0, tp["background"]),
                (position_set_x, pos1, tp["tabwidth"]),
                (position_set_y, pos1, tp["tabheight"]),
                (overlay_set_size, reg0, pos1),
                (position_set_x, pos1, x),
                (position_set_y, pos1, y + 2),
                (overlay_set_position, reg0, pos1),
                (overlay_set_color, reg0, 0xFFBBBBBB),
                ])
            code.extend([
                (try_begin),
                    ] + conditions + [
                    (create_button_overlay, butvar, strname, tf_center_justify),
                    (overlay_set_color, butvar, color),
                (else_try),
                    (create_text_overlay, butvar, strname, tf_center_justify),
                    (overlay_set_color, butvar, 0x808080),
                (try_end),
                (position_set_x, pos1, x + tp["deltax"] / 2),
                (position_set_y, pos1, y + tp["deltay"] / 2),
                (overlay_set_position, butvar, pos1),
                ])
            actcode.extend([
                (else_try),
                    (eq, ":object", butvar),
                    (try_begin),
                        ] + conditions + [
                        (presentation_set_duration, 0),
                        (start_presentation, prsnt),
                    (try_end),
                ])
#            print x, y
            i += 1
            x += tp["deltax"]
            y += tp["deltay"]
            if ("perline" in tp) and (i % tp["perline"] == 0):
                sx += tp["delta2x"]
                sy += tp["delta2y"]
                x = sx
                y = sy
                i = 0
                
        return code, actcode

    def getGenericDisplay(self, columns, yadd, background, menupos, contpos, captioncode,
                extra=[[],[]], tabposition=None, color=0x000000):
        code = []
        total_height = self.getTotalHeight(yadd)
        actiondisplays = self.getActionDisplayCode(columns, yadd, color)
        code.extend([
                    (self.vid, prsntf_manual_end_only, 0, [
                        (ti_on_presentation_load, [
                            (set_fixed_point_multiplier, 1000),
                            (assign, "$g_menu_ready", 0),
                            (create_mesh_overlay, reg0, background),
                            (position_set_x, pos1, menupos[0]),
                            (position_set_y, pos1, menupos[1]),
                            (overlay_set_position, reg0, pos1),
                            (position_set_x, pos1, menupos[2]),
                            (position_set_y, pos1, menupos[3]),
                            (overlay_set_size, reg0, pos1),

                            (str_clear, s0),
                            (create_text_overlay, "$g_presentation_obj_container", s0, tf_scrollable),
                            (position_set_x, pos1, contpos[0]),
                            (position_set_y, pos1, contpos[1]),
                            (overlay_set_position, "$g_presentation_obj_container", pos1),
                            (position_set_x, pos1, contpos[2]),
                            (position_set_y, pos1, contpos[3]),
                            (overlay_set_area_size, "$g_presentation_obj_container", pos1),
                            (set_container_overlay, "$g_presentation_obj_container"),
                            (assign, ":cur_y", total_height),
                            ] + captioncode + [
                            ] + actiondisplays + [
                            (set_container_overlay, -1),
                            ] + extra[0] + [
                            # tabs for admin panel
                            # back and start map buttons for admin panel
                            (presentation_set_duration, 999999),
                            (assign, "$g_menu_ready", 1),
                            ]),
                        (ti_on_presentation_event_state_change, [
                            (store_trigger_param_1, ":object"),
                            (store_trigger_param_2, ":value"),
                            (try_begin),
                                (eq, "$g_menu_ready", 0),
                            (else_try),
                                # todo: the extra buttons for admin panel (start, back)
                                # (eq, ":object", "$g_presentation_obj_admin_panel_13"),
                                # (presentation_set_duration, 0),
                                ] + self.getActionCode(extra[1]) + [
                            (try_end),
                            ]),
                        (ti_on_presentation_run, [
                            (try_begin),
                                (key_clicked, key_escape),
                                (presentation_set_duration, 0),
                            (try_end),
                            ]),
                        ])
                    ])
        return code

    def getActionCode(self, extra_actions):
        code = []
        code.extend([
                    (try_begin),
                        (eq, 1,2), # for easier looping
                    ])
        code.extend(getActionCodeFor(self.getActionObjects()))
        code.extend(extra_actions)
        code.append((try_end))
        return code


################################################################################
################################################################################
# Defining some generators for ingame script_s
################################################################################
################################################################################

def getSendNirecotiveInitials(all_items):
    content_code = [
                (store_script_param, ":player", 1),
                ]
    for item in all_items:
        if 'getSendInitial' in dir(item):
            content_code.extend(item.getSendInitial())
        elif isinstance(item, Item) and hasattr(item, 'sendInitialHandler'):
            content_code.extend(item.sendInitialHandler)
    code = [("send_nirecotive_initials", content_code)]
    return code

def string_sel_func(saving):
    retarr = []
    for i in range(1, 68):
        if saving:
            retarr.extend([
                    (else_try),
                        (eq, ":id", i),
                        (str_store_string_reg, i, s0)
                    ])
        else:
            retarr.extend([
                    (else_try),
                        (eq, ":id", i),
                        (str_store_string_reg, s0, i)
                    ])
    return retarr


def getExtraScripts():
    return [
                    ("string_register_load", [
                        (store_script_param, ":id", 1),
                        (try_begin),
                            (eq, ":id", 0),
                            # s0 to s0 ...
                            ] + string_sel_func(False) + [
                        (try_end),
                    ]),

                    ("string_register_save", [
                        (store_script_param, ":id", 1),
                        (try_begin),
                            (eq, ":id", 0),
                            # s0 to s0 ...
                            ] + string_sel_func(True) + [
                        (try_end),
                    ]),
                    ] + getSendNirecotiveInitials(all_items) + [
                    ] + checkOutOfMenuScript() + [
                ]

def get_default_initialization():
    global all_items
    code = []
    for item in all_items:
        if hasattr(item, "initialize"):
            code.extend(item.initialize)
        elif isinstance(item, clientStringItem) and hasattr(item, "stringreg"):
            code.append((str_store_string, item.stringreg, item.str_id()+"_default"))
    return code

def get_zero_initialization():
    '''
    This function exists to get rid of "Usage of unassigned global variable"
    and allows compiler to mark that we have this kind of variable which in
    turn allows nirecotive default setter to set it.
    '''
    global all_items
    incode = []
    for item in all_items:
        if isinstance(item, Item):
            if item.vartype in ['int', 'dropbox', 'onlyzeroinit']:
                incode.append((assign, item.var_id(), 0))
    code = [
                ("zero_init_never_used", [
                    ] + incode + [
                ]),
    ]
    return code

################################################################################
################################################################################
# Other ingame code generation
################################################################################
################################################################################
def getTroopCode(all_items):
    code = []
    for item in all_items:
        if isinstance(item, Item) and hasattr(item, 'troops'):
            code.extend(item.troops)
    return code

def getNetworkCode(all_actions):
    '''
    Call with all actions with network code. The result needs to be added to
    the end of "game_receive_network_message" in module_scripts.py
    '''
    code = []
    server_actions = []
    client_actions = []
    for a in all_actions:
        if isinstance(a, Item):
            if hasattr(a, "serverHandler"):
                server_actions.extend([
                            (eq, ":muxed_type", a.get_channel("server")),
                            ] + a.serverHandler + [
#(assign, reg0, ":val1"),
#] + ((hasattr(a, "caption") and [
#(str_store_string, s0, a.str_id()),
#]) or [(str_store_string, s0, "str_yes")]) + [
#(display_message, "@got {reg0} on channel {s0}"),
                        (else_try),])
            if hasattr(a, "clientHandler"):
                client_actions.extend([
                            (eq, ":muxed_type", a.get_channel("client")),
                            ] + a.clientHandler + [
                        (else_try),])
    code.extend([
                    (try_begin),
                        (eq, ":event_type", mp_nir_server),
                        (multiplayer_is_server),
                        (store_script_param, ":muxed_type", 3),
                        (assign, ":val2", 0),
                        (assign, ":val3", 0),
                        (store_script_param, ":val1", 4),
                        (store_script_param, ":val2", 5),
                        (store_script_param, ":val3", 6),
                        (get_max_players, ":num_players"),
                        (try_begin),
                            ] + server_actions + [
                        # else
                            # unknown event
                        (try_end),
                    (else_try),
                        (eq, ":event_type", mp_nir_client),
                        (neg|multiplayer_is_dedicated_server),
                        (store_script_param, ":muxed_type", 3),
                        (assign, ":val2", 0),
                        (assign, ":val3", 0),
                        (store_script_param, ":val1", 4),
                        (store_script_param, ":val2", 5),
                        (store_script_param, ":val3", 6),
                        (get_max_players, ":num_players"),
                        (try_begin),
                            ] + client_actions + [
                        # else
                            # unknown event
                        (try_end),
                    (else_try),
                        (eq, ":event_type", multiplayer_event_nir_store_string),
                        (neg|multiplayer_is_server),
                        (str_store_string_reg, s52, s0),
                    (else_try),
                        (eq, ":event_type", multiplayer_event_nir_store_string_server),
                        (try_begin),
                            ] + checkAdmin(":player_no") + [
                            (str_store_string, s52, s0),
                        (try_end),
                    (else_try),
                        (eq, ":event_type", multiplayer_event_nir_store_string_server_weak),
                        (str_store_string, s54, s0),
                        (assign, "$g_weak_string_owner", ":player_no"),
                    (try_end),
                    ])
    return code




def getStringCode(all_items):
    '''
    Call with all items which require some strings. The result needs to be
    added to the end of list strings in module_strings.py
    '''
    def uniquefyStrings(strings):
        res = []
        for (key, s) in strings:
            if (key, s) in res:
                continue
            res.append((key, s))
        return res
    strings = []
    for item in all_items:
#        if isinstance(item, Item):
#            print hasattr(item, "strings")
#            if hasattr(item, "strings"):
#                print item.strings
        if isinstance(item, Item) and hasattr(item, "strings"):
            strings.extend(item.strings)
        elif 'getStrings' in dir(item):
            strings.extend(item.getStrings())
    # need uniqufying todo
    return uniquefyStrings(strings)
    
def getMenuCode(all_items):
    '''
    Call with all items which are menus. The result needs to be added to the
    end of presentations in module_presentations.py.
    '''
    code = []
    for item in all_items:
        if isinstance(item, Menu):
            code.extend(item.getPresentation())
    return code

def getExtraChannelProcessing():
    '''
    '''
    code = []
    for item in all_items:
        if isinstance(item, extendChannelItem):
            channel = item.other.get_channel(item.side)
            if item.side == "server":
                code.extend([
                    (try_begin),
                        (eq, ":event_type", mp_nir_server),
                        (multiplayer_is_server),
                        (store_script_param, ":muxed_type", 3),
                        (eq, ":muxed_type", channel),
                        (store_script_param, ":val1", 4),
                        (store_script_param, ":val2", 5),
                        (store_script_param, ":val3", 6),
                        ] + item.content + [
                    (try_end),
                    ])
            if item.side == "client":
                code.extend([
                    (try_begin),
                        (eq, ":event_type", mp_nir_client),
                        (store_script_param, ":muxed_type", 3),
                        (eq, ":muxed_type", channel),
                        (store_script_param, ":val1", 4),
                        (store_script_param, ":val2", 5),
                        (store_script_param, ":val3", 6),
                        ] + item.content + [
                    (try_end),
                    ])
    return code



###############################################################################
###############################################################################
# Define some useful action channels and other Nirecotive core messaging
###############################################################################
###############################################################################
constString("{s0}{s1}", "s0s1")

string_copying = channelItem("string_copying", channel=[mp_copy_string])
string_copying.serverHandler = [
                    ] + checkAdmin(":player_no") + [
                    # val3 as distribute to admins
                    (call_script, "script_string_register_load", ":val2"), # s0 loaded here
                    (call_script, "script_string_register_save", ":val1"),
                    (try_begin),
                        (eq, ":val3", 1), # share to admins
                        ] + sendToAll('admin', [
#                            (multiplayer_send_3_int_to_player, mp_nir_client, mp_copy_string, ":val1", ":val2"),
                            (multiplayer_send_string_to_player, ":player", multiplayer_event_nir_store_string, s0),
                            (multiplayer_send_3_int_to_player, ":player", mp_nir_client, mp_copy_string, ":val1", ":val2", 0),
                        ]) + [
                    (try_end),
                ]
string_copying.clientHandler = [
                    (neg|multiplayer_is_server),
                    # val3 as catenate
                    (try_begin),
                        (eq, ":val3", 1),
                        (call_script, "script_string_register_load", ":val2"),
                        (str_store_string_reg, s1, s0),
                        (call_script, "script_string_register_load", ":val1"),
                        (str_store_string, s0, "str_s0s1"),
                        (call_script, "script_string_register_save", ":val1"),
                    (else_try),
                        (call_script, "script_string_register_load", ":val2"),
                        (call_script, "script_string_register_save", ":val1"),
                    (try_end),
                ]
string_copying.document = "copies string from one register to the other."
string_sending = channelItem("string_sending", channel = [mp_event_debug_static_string])
string_sending.serverHandler = [
                    ] + checkAdmin(":player_no") + [
                    (store_add, ":stridx", "str_no_string", ":val1"),
                    (multiplayer_send_string_to_player, ":cur_player", multiplayer_event_show_server_message, ":stridx"),
                ]
string_sending.document = "returns a string value of given index"


###############################################################################
###############################################################################
# Versioning code
###############################################################################
###############################################################################

nir_version = '.'.join([str(c) for c in nir_version_as_list])
major_values = {'Native':0,
                'Deprecated1':1,
                'Nirecotive':2,
                'Custom Nirecotive':3,
                'Unknown':4,
                }
major_strings = {}
for s, val in major_values.items():
    major_strings[s] = constString(s + " {reg0}.{reg1}.{reg2}")
native_string = constString('Native')
unknown_string = constString('Unknown {reg0}.{reg1}.{reg2}')
this_mod_string = constString(this_mod + " " + nir_version)
nir_version_as_number = 0x1000000 * major_values[this_mod]
for c in range(len(nir_version_as_list)):
    nir_version_as_number += 0x100**(2-c) * nir_version_as_list[c]

def getThisModMux():
    if this_mod in major_values:
        return major_values[this_mod]
    return 0

def getThisModVersion():
    return nir_version_as_number

def stringToVersion(s):
    part = map(int, s.split('.')[-3:])
    return (part[0]<<16) & (part[1]<<8) & part[2]
    
def serverAboveVersion(version):
    return [
                (eq, "$g_s_mod_mux", getThisModMux()),
                (ge, "$g_s_module_version", stringToVersion(version)),
            ]
def serverNotNative():
    return [
                (ge, "$g_s_module_version", 1),
            ]
def checkPlayerHasThisMod(player, version="0.0.0", othermod=None):
    targetmod = othermod
    if not targetmod:
        targetmod = major_values[this_mod]
    else:
        targetmod = major_values[othermod]
    return [
                (player_get_slot, ":nirversion", player, 52),
                (assign, "$g_server_version", ":val1"),
                (store_and, ":mod_mux", ":nirversion", 0x3f000000),
                (val_div, ":mod_mux", 0x1000000),
                (store_and, ":mod_version", ":nirversion", 0xffffff),
#(assign, reg0, ":mod_mux"),
#(assign, reg1, ":mod_version"),
#(assign, reg2, stringToVersion(version)),
#(display_message, "@checking mod equality ({reg0}, {reg1}, {reg2})"),
                (eq, ":mod_mux", targetmod),
                (ge, ":mod_version", stringToVersion(version)),
                ]


# slot in player data
nirecotive_version = Slot("player", 52)


# action channel for informing nirecotive version between client and server.
versioning_channel = channelItem("versioning_channel", channel=[249])
versioning_channel.document="Initial version greeting"
versioning_channel.clientHandler=[
                    (assign, "$g_native_server", 0), # for compatibility with N2 servers
                    (assign, "$g_server_version", ":val1"),
                    (store_and, "$g_s_mod_mux", "$g_server_version", 0x3f000000),
                    (val_div, "$g_s_mod_mux", 0x1000000),
                    (store_and, "$g_s_module_version", "$g_server_version", 0xffffff),
                    # send client version to server
                    (multiplayer_send_2_int_to_server, mp_nir_server, versioning_channel.get_channel(), nir_version_as_number),
                    # display client version
                    (display_message, this_mod_string.str_id()),
                ]
versioning_channel.serverHandler=[
                    # store information about player client version
                    (player_set_slot, ":player_no", nirecotive_version.slot(), ":val1"),
                    # continue to sending nirecotive initial values, as the
                    # client can read them.
                    (call_script, "script_send_nirecotive_initials", ":player_no"),
                ]

# action channel for quering nirecotive version of some player
version_query = serverButtonItem("Query mod version", channel=[250,250])
version_query.document="Querying version of some other player"
def mux_version_query():
    ret = [(try_begin)]
    for name, idx in major_values.items():
        ret.extend([
                    (eq, ":val", idx),
                    (multiplayer_send_string_to_player, ":player_no", multiplayer_event_show_server_message, major_strings[name].str_id()),
                (else_try),
                ])
    ret.extend([
                    (multiplayer_send_string_to_player, ":player_no", multiplayer_event_show_server_message, unknown_string.str_id()),
                (try_end),
                ])
    return ret
version_query.serverHandler=[
                # query version from other client
                (player_get_slot, ":ver", ":val1", nirecotive_version.slot()),
                (try_begin),
                    (gt, ":ver", 0x10000),
                    (store_and, reg0, ":ver", 0xff0000),
                    (store_and, reg1, ":ver", 0xff00),
                    (store_and, reg2, ":ver", 0xff),
                    (store_and, ":val", ":ver", 0x7f000000),
                    (val_div, reg0, 0x10000),
                    (val_div, reg1, 0x100),
                    (val_div, ":val", 0x1000000),
                    ] + mux_version_query() + [
                (else_try),
                    (multiplayer_send_string_to_player, ":player_no", multiplayer_event_show_server_message, native_string.str_id()),
                (try_end),
                ]
#version_query.actionHandler = [
#                (multiplayer_send_3_int_to_server, mp_nir_server, version_query.get_channel(), selected_player.var_id()),
#                ]



send_initial_version_query = [
                # after getting this, the client will ask the server to send
                # all nirecotive information.
                # sends the server version as server chat
                (multiplayer_send_string_to_player, ":player_no", multiplayer_event_show_server_message, this_mod_string.str_id()),
                # informs the client of the server version in number format
                (multiplayer_send_2_int_to_player, ":player_no", mp_nir_client, versioning_channel.get_channel(), nir_version_as_number)
                ]




###############################################################################
###############################################################################
# The getModCommands function which returns the final code pieces
###############################################################################
###############################################################################

def getModCommands():
    '''
    This function returns mods to modcombiner
    '''
    global all_items
    modcommands = []
    modcommands.extend([
        ModMod("extend", "scripts", getNetworkCode(all_items) + getExtraChannelProcessing(),
                path=[["game_receive_network_message",1]],
                name="menu_new_extend_net"),
        ModMod("extend", "presentations", getMenuCode(all_items),
                name="menu_presentations"),
        ModMod("extend", "strings", getStringCode(all_items),
                name="menu_strings"),
        ModMod("extend", "scripts", getExtraScripts(),
                name="menu_extra_scripts"),
        ModMod("extend", "scripts", getSendNirecotiveInitials(all_items),
                name="menu_send_initials"),
        ModMod("extend", "scripts", get_zero_initialization(),
                name="zero init not used"),
        ModMod("extend", "scripts", [(call_script, "script_send_nirecotive_initials", ":player_no")],
                path=[["multiplayer_send_initial_information",1]],
                name="menu_call_send_initials"),
        ModMod("insert", "scripts", [(try_end)],
                path=[["game_receive_network_message",1]],
                insert_location=1,
                insert_relative_to=(display_message, "str_server_s0", 0xFFFF6666),
                name="fix TW game_receive_network_message"),
        ModMod("extend", "scripts", [
                    ("initialize_nirecotive_variables",
                        get_default_initialization(),
                    ),
                    ("initialize_nirecotive_rewrittable",
                        [],
                    ),
                ], name="add nirecotive variable initialization scripts"),
        ModMod("extend", "scripts", [
                    (try_begin),
                        (neq, "$g_variables_initialized", 1),
                        (assign, "$g_variables_initialized", 1),
                        (call_script, "script_initialize_nirecotive_variables"),
                        (call_script, "script_initialize_nirecotive_rewrittable"),
                    (try_end),
                ], path=[["game_quick_start",1]],
                name="call nirecotive initialization scripts"),
        ModMod(mode="extend",
                target_var="scripts",
                content=send_initial_version_query,
                path=["multiplayer_send_initial_information",1],
                name="send initial version query"),
        ])
#            ["extend", "scripts", [["game_receive_network_message",1]], getNetworkCode(all_items)],
#            ["extend", "presentations", [], getMenuCode(all_items)],
#            ["extend", "strings", [], getStringCode(all_items)],
#            ["extend", "scripts", [], getExtraScripts()],
    return modcommands

###############################################################################
###############################################################################
# Some tool checks for checking the validity of modmods
# and other functions for external tools
###############################################################################
###############################################################################

def check_channel_uniquity():
    '''
    Checks that there is no colliding channels
    '''
    global all_items
    channel_to_item = {}
    stringregs = {}
    for item in all_items:
        if hasattr(item, "channel"):
            channels = set()
            channels.add(item.get_channel("client"))
            channels.add(item.get_channel("server"))
            for c in channels:
                if c in channel_to_item and channel_to_item[c] != item:
                    print "Error, colliding channel %d with '%s' and '%s'" % (c, item, channel_to_item[c])
                else:
                    channel_to_item[c] = item
        if hasattr(item, "stringreg"):
            if item.stringreg in stringregs and stringregs[item.stringreg] != item:
                print "Error, colliding string register %d with '%s' and '%s'" % (item.stringreg, stringregs[item.stringreg], item)
    print "check done"

def output_variables_for_init():
    global all_items
    itemdict = {}
    for item in all_items:
        if isinstance(item, Item):
            itemdict[item.vid] = item
    processed = []
    old_values = {}
    if os.path.exists("newnirvars.txt"):
        with open("newnirvars.txt") as f:
            lnum = 0
            for line in f.readlines():
                lnum += 1
                line = line.strip()
                if line == "":
                    continue
                if line[0] == "#":
                    continue
                word = line.split()
                vid = word[1]
                if not vid in itemdict:
                    print "Error: item doesn't exist anymore: '%s', on line %d. Removing" % (vid, lnum)
                    print line
                    continue
                if word[0] != itemdict[vid].vartype:
                    print "Error: vartype does not match, ignoring old value"
                    print line
                    continue
                if word[0] == 'int':
                    old_values[word[1]] = ['int', int(word[2])]
                elif word[0] == 'string':
                    strings = line.split('"')
                    if len(strings) < 2:
                        print "Error: improper string line, on line %d" % lnum
                        print line
                        continue
                    old_values[word[1]] = ['string', strings[1]]
                elif word[0] == 'dropbox':
                    strings = line.split('"')
                    if len(strings) < 2:
                        print "Error: improper dropbox line, on line %d" % lnum
                        print line
                        continue
                    choices = []
                    for i in range(3,len(strings),2):
                        choices.append(i)
                    old_values[word[1]] = ['dropbox', strings[1], choices]
                    if strings[1] not in itemdict[vid].choices:
                        print "Error: no such choice: '%s', for item '%s', on line %d" % (strings[1], vid, lnum)
    f = open("newnirvars.txt", "w")
    for menu in all_items:
        if not isinstance(menu, Menu):
            continue
        print >>f, ""
        print >>f, ""
        print >>f, "#"*80
        print >>f, "### " + menu.caption
        for a in menu.actions:
            if isinstance(a, str):
                continue
            elif isinstance(a, Item):
                if hasattr(a, 'initialize'):
                    # this item has custom initialization code
                    continue
                if a.vartype == 'unknown':
#                    print "Error: unknown vartype, can't save for initialization"
                    continue
                vid = a.vid
                processed.append(vid)
                if hasattr(a, "caption"):
                    print >>f, "# " + a.caption,
                if hasattr(a, "document"):
                    print >>f, "# " + a.document,
                print >>f, ""
                if a.vartype == 'int':
                    val = 0
                    if vid in old_values:
                        val = old_values[vid][1]
                    else:
                        print >>f, "######## NEW ########"
                    print >>f, "int".ljust(10), vid.ljust(40), val
                elif a.vartype == 'string':
                    val = '" "'
                    if vid in old_values:
                        val = '"'+old_values[vid][1]+'"'
                    else:
                        print >>f, "######## NEW ########"
                    print >>f, "string".ljust(10), vid.ljust(40), val
                elif a.vartype == 'dropbox':
                    sel = ""
                    if vid in old_values:
                        sel = old_values[vid][1]
                    else:
                        sel = a.choices[0]
                    print >>f, "dropbox".ljust(10), vid.ljust(40), '"'+sel+'"',
                    print >>f, "# out of: [",
                    for ch in a.choices:
                        print >>f, '"'+ch+'",',
                    print >>f, "]"
    print >>f, ""
    print >>f, ""
    print >>f, "#"*60
    print >>f, "#"*60
    print >>f, "#"*60
    print >>f, "# not in any menu"
    for item in all_items:
        if isinstance(item, Item):
            if hasattr(item, 'initialize'):
                # this item has custom initialization code
                continue
            vid = item.vid
            if not vid in processed:
                if item.vartype == 'unknown':
                    print "Error: unknown vartype, can't save for initialization, item: '%s'" % vid
                    continue
                processed.append(vid)
                if hasattr(vid, "caption"):
                    print >>f, "# " + item.caption,
                if hasattr(vid, "document"):
                    print >>f, "# " + item.document,
                if item.vartype == 'int':
                    print >>f, ""
                    val = 0
                    if vid in old_values:
                        val = old_values[vid][1]
                    else:
                        print >>f, "######## NEW ########"
                    print >>f, "int".ljust(10), vid.ljust(40), val
                elif item.vartype == 'string':
                    print >>f, ""
                    val = '" "'
                    if vid in old_values:
                        val = '"'+old_values[vid][1]+'"'
                    else:
                        print >>f, "######## NEW ########"
                    print >>f, "string".ljust(10), vid.ljust(40), val
                elif item.vartype == 'dropbox':
                    print >>f, ""
                    sel = ""
                    if vid in old_values:
                        sel = old_values[vid][1]
                    else:
                        sel = item.choices[0]
                    print >>f, "dropbox".ljust(10), vid.ljust(40), '"'+sel+'"',
                    print >>f, "# out of: [",
                    for ch in item.choices:
                        print >>f, '"'+ch+'",',
                    print >>f, "]"
    f.close()



def print_code(code, indent=0):
    '''
    Debug function for printing some piece of modulesystem code. Translates the
    command words into text representation, but leaves other integer values as
    they are.
    '''
    reverse_op = dict(filter(lambda x: isinstance(x[0], int), 
                map(lambda x: (x[1],x[0]), 
                    header_operations.__dict__.items())))
    reverse_op[else_try] = 'else_try'
    indentstr = "    "
    for nc in code:
        res = []
        flag_neg = False
        flag_or = False
        if isinstance(nc, (int, long)):
            if nc & neg:
                flag_neg = True
                nc = nc ^ neg
            if nc & this_or_next:
                flag_or = True
                nc = nc ^ this_or_next
            res.append(reverse_op[nc])
            if flag_neg:
                res[0] = "neg|" + res[0]
            if flag_or:
                res[0] = "this_or_next|" + res[0]
        else:
            res.extend(nc)
            if isinstance(res[0], (list, tuple)) and len(res) < 1:
                continue
            haslist = False
            for r in res:
                if isinstance(r, list):
                    haslist = True
            if haslist:
                # function declaration or something else strange
                print indentstr*indent,
                print "(",
                for token in res:
                    if isinstance(token, list):
                        print "["
                        print_code(token, indent + 1)
                        print indentstr*indent + "]",
                        pass
                    else:
                        if isinstance(token, str):
                            print '"'+token+'",',
                        else:
                            print str(token) + ",",
                print "),"
                continue
            else:
                res[0] = reverse_op[res[0]]
        nc = tuple(res)
        comm = nc[0]
        if comm in ['try_end', 'else_try']:
            indent -= 1
        print indentstr*indent + str(nc) + ","
        if comm in ['try_begin', 'else_try'] or 'try_for' in comm:
            indent += 1


