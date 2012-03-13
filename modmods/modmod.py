


class ModMod:
    '''
    Structure to pass modmod information. Modmods are applied to the module
    system by modcombiner during the compilation of the mod.

    mode
        'extend'
            Will extend the defined target with the contents of this mod.
        'replace'
            Will replace the contents of the defined target with the contents
            of this mod.
        'insert'
            This mode is somewhat messy, as it inserts code in the middle of
            the base code, so use this with caution. If you can instead
            implement what you want with extend or replace, consider using them
            instead. This will place the contents of this mod to the location
            specified with insert_location to the target of this mod.
    targe_var
        The name of the root variable of the target. For example, 'scripts' or
        'presentations'.
    content
        The contents of this mod as module system code. For example, one script
        for 'scripts' or script contents for some script.
    path
        path to the actual target, if you don't intend to operate on the target
        root. This is list of pairs (two element list). First being the name of
        that layer, for exmple, name of the script. Second being the field in
        the matching tuple as integer. For scripts the field is 1 (as the
        content is the second field of the tuple). For presentations the field
        is 3 (as the content is the fourth field).
    insert_location
        If the mode is insert, this will define the location in the target to
        which the mod will be applied.
    insert_relative_to
        if defined, the insert mode will insert the content relative to the
        lines matching the one given as this parameter. This will make the mod
        applying even messier, if possible, try to avoid any insert mode mods.
    runtime_check
        A function to run during the applying to make some final tuning for the
        mod. On most cases this can be left as None. The function must take two
        arguments, first the modmod itself and second the variable the modmod
        is changing or actually the layer of that variable. Use the passed
        variable as read only and do not change modmod's mode or target_var.
    '''
    def __init__(self, mode, target_var, content, 
                path=[], 
                name="",                # it is a good habit to give names to mods
                insert_location=0,   # only needed for insert mode
                insert_relative_to=None,# insert relative to the matching line
                runtime_check=None,     # needed currently for searching insert location
                ):
        self.mode = mode
        self.target_var = target_var
        self.content = content
        self.path = path
#        self.name = name
        self.name = name.replace(" ", "_")
        self.insert_location = insert_location
        self.insert_relative_to = insert_relative_to
        self.runtime_check = runtime_check

