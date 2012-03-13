'''
Combines modmods into warband module during normal module compilation.

The mods should be placed into subdirectory modmods. And mods should have
function getModCommands(), which returns ModMod objects (defined in
modmods.modmod) representing differenct module pieces forming that mod.

python modcombiner.py
    Run this file in the module system directory to write necessary binds to
    the module system files for applying mods.

python modcombiner.py names
    will print the names of all enabled mods and the amount of unnamed mods.

python modcombiner.py content <modname>
    will attempt to print the contents of the given mod, but some information
    is lost due to the format of warband mods.

python modcombiner.py content
    Like above, but will print the content of all mods.

python modcombiner.py test
    Will attempt to simulate the mod applying, but doesn't work that well due
    to problems with getting fake-targets from somewhere. Currently tests only
    the mods targetting the root target.
'''

import sys, os
sys.path.append(".")
import header_operations
import logging
import copy

applied_mods = []

def applyMod(target, path, mod):
    '''
    Applies one mod to the given target. Traverses the target according to the
    given path. The initial target and path are taken from the mod.
    '''
    if path and isinstance(path, list):
        count = 0
        token, field = path[0]
        for part in target:
            if len(part) == 0:
                return count
            try:
                if part[0] == token or token == '*' or \
                        (isinstance(token, str) and isinstance(part[0], str) and \
                        token[0] == '*' and token[-1] == '*' and token[1:-1] in part[0]):
                    count += applyMod(part[field], path[1:], mod)
            except Exception, err:
                print err
                print part
                print mod.path
                print mod.name
                raise Exception(err)
        return count
    else:
        if mod.runtime_check:
            mod.runtime_check(mod, target)
        if mod.mode == "extend":
            target.extend(mod.content)
        if mod.mode == "replace":
            target[:] = mod.content
        if mod.mode == "insert":
            i = mod.insert_location
            if mod.insert_relative_to:
                count = 0
                newtarget = copy.copy(target)
                for line_i, line in enumerate(target):
                    if line == mod.insert_relative_to:
                        count += 1
                        newtarget[line_i+i:line_i+i] = mod.content
                target[:] = newtarget
                if count > 0:
                    applied_mods.append(mod.name)
                return count
            else:
                target[i:i] = mod.content
        applied_mods.append(mod.name)
        return 1

def applyMods(initial_target, mods):
    '''
    Applies all mods which match to the given top level initial target.
    '''
    mods.sort(key = lambda x: x.insert_location)
    for mod in mods:
#        variable = mod.target_var
        if mod.name in applied_mods:
            continue
#        print "applying", mod.name
        path = mod.path
        if isinstance(path, list):
            if len(path) > 0:
                if isinstance(path[0], list):
                    pass
                else:
                    path = [path]
        else:
            logging.error("invalid modmod path: %s" % str(path))
            path = []
        target = initial_target
        applyCount = applyMod(target, path, mod)

def getMainTargets(mods):
    '''
    Returns all the different top level targets the mods have.
    '''
    targets = map(lambda x: x.target_var, mods)
    targets = list(set(targets))
    return targets

def getModmods():
    '''
    Imports all files from modmods folder and gets all mods from them using
    getModCommands() function, which should be present in the mod.
    '''
    files = os.listdir('modmods')
    files = filter(lambda x: x[-3:] == '.py', files)
    files = filter(lambda x: x[0] != '_', files)
    files = map(lambda x: x[:-3], files)
    files = map(lambda x: 'modmods.' + x, files)
    modules = []
    for f in files:
        # if not os.path.isidr() TODO
        modules.append(__import__(f, fromlist=['modmods']))
    modmods = []
    for m in modules:
        if hasattr(m, 'getModCommands'):
            modmods.extend(m.getModCommands())
    modmods = uniquefyMods(modmods)
    return modmods

def uniquefyMods(mods):
    '''
    Removes duplicate mods from the mods list. For some reason some mods get
    applied quite many times.
    '''
    res = []
    check = []
    for m in mods:
        if m.name in check:
            continue
        else:
            res.append(m)
            check.append(m.name)
    return res

def detectModdables(parentdir):
    '''
    Applies modmods to all valid and matching targets that are found from the
    bound file.
    '''
    mods = getModmods()
    targets = getMainTargets(mods)
    for target in targets:
        if target in parentdir.keys():
            initial_target = parentdir[target]
            scriptmods = filter(lambda x: x.target_var == target, mods)
            applyMods(initial_target, scriptmods)


def print_code(code, indent=0):
    '''
    Debug function for printing some piece of modulesystem code. Translates the
    command words into text representation, but leaves other integer values as
    they are.
    '''
    reverse_op = dict(filter(lambda x: isinstance(x[0], int), 
                map(lambda x: (x[1],x[0]), 
                    header_operations.__dict__.items())))
    reverse_op[header_operations.else_try] = 'else_try'
    indentstr = "    "
    for nc in code:
        res = []
        flag_neg = False
        flag_or = False
        if isinstance(nc, (int, long)):
            if nc & header_operations.neg:
                flag_neg = True
                nc = nc ^ header_operations.neg
            if nc & header_operations.this_or_next:
                flag_or = True
                nc = nc ^ header_operations.this_or_next
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
                if res[0] in reverse_op:
                    res[0] = reverse_op[res[0]]
        nc = tuple(res)
        comm = nc[0]
        if comm in ['try_end', 'else_try']:
            indent -= 1
        print indentstr*indent + str(nc) + ","
        if comm in ['try_begin', 'else_try'] or isinstance(comm, str) and 'try_for' in comm:
            indent += 1

def usage(name):
    print"""
python %s <mode> <extra>

modes
    bind [yes]
        default mode, which will bind all module system files for modcombiner.
        If yes is set, will answer automatically yes.
    test
        deprecated
    content <name>
        will list the content of the mod with the given name
    names
        will list all names of enabled mods and count of unnamed ones
    newmenuwriteinit
        writes out init file for nirecotive default setter.
    newmenucheck
        prints the output from newmenu checks
""" % name

if __name__ == '__main__':
    mode = "bind"
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    if mode == "bind":
        answer = 'yes'
        if not 'yes' in sys.argv:
            answer = raw_input(
"""Running this file will write bindings required for modmods into all module
system files. Are you sure (Y/N): """)
            if not answer.lower() in ["y", "yes"]:
                usage(sys.argv[0])
                print "Action cancelled, press enter to exiting"
                sys.stdin.readline()
                sys.exit()
        # modmods __init__.py
        f = open(os.path.join('modmods', '__init__.py'), 'w')
        print >>f, ""
        f.close()
        # module system files
        files = os.listdir('.')
        files = filter(lambda x: x[:7] == 'module_', files)
        files = filter(lambda x: x[-3:] == '.py', files)
        print files
        for fname in files:
            if fname == "module_constants.py":
                continue
            f = open(fname)
            lines = f.readlines()
            lines = map(lambda x: x.rstrip(), lines)
            if "# Modmod combiner" in lines:
                # the modcombiner is already bound into this file, do nothing
                print fname.ljust(30), "already bound earlier"
            else:
                f.close()
                f = open(fname, "a")
                print >>f, "# Modmod combiner"
                print >>f, "import modcombiner"
                print >>f, "modcombiner.detectModdables(globals())"
                f.close()
                print fname.ljust(30), "successfully bound"
        if not 'yes' in sys.argv:
            print "Press enter to exit"
            sys.stdin.readline()
    elif mode == "test":
        mods = getModmods()
        targets = getMainTargets(mods)
        parent = {}
        for target in targets:
            parent[target] = []
        detectModdables(parent)
        for k, p in parent.items():
            print '-'*60
            print k
            print_code(p)
    elif mode == "content":
        mods = getModmods()
        for m in mods:
            if len(sys.argv) <= 2 or m.name == sys.argv[2]:
                print_code(m.content)
    elif mode == "names":
        mods = getModmods()
        unnamed = 0
        for m in mods:
            if m.name == "":
                unnamed += 1
            else:
                print m.name
        print unnamed, "unnamed mods"
    elif mode == "newmenuwriteinit":
        mods = getModmods()
        from modmods import nirecotive_core
        nirecotive_core.output_variables_for_init()
    elif mode == "newmenucheck":
        mods = getModmods()
        from modmods import nirecotive_core
        nirecotive_core.check_channel_uniquity()
