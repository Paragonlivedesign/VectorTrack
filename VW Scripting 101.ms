Great. I’ll dig deep into how Vectorworks scripting works—both VectorScript and Python—and how to develop plugins across all types (objects, tools, menu commands, event-based plugins) specifically for the 2025 version on Windows. I’ll compile a comprehensive how-to guide with clear explanations, code examples, and development workflow instructions.

I’ll let you know as soon as the full document is ready.


# Building Plugins in Vectorworks 2025 (Windows)

Developing custom plugins in **Vectorworks 2025** allows you to extend the software’s functionality using either **VectorScript** (a Pascal-like language) or **Python**. This comprehensive guide walks through the process of setting up your environment, creating different plugin types (menu commands, tools, and parametric objects), and provides code examples in both VectorScript and Python. The guide also covers advanced topics like event-driven plugins, using external libraries in Python, and distributing your plugins. All instructions are tailored for **Vectorworks 2025 on Windows**.

## Overview of the Vectorworks Plugin System

Vectorworks supports several scripting options to customize and automate tasks: **VectorScript**, **Python**, and even a C++ SDK and visual scripting (Marionette). We will focus on VectorScript and Python, which can create **scripted plug-ins** that integrate into the Vectorworks interface. These plugins function just like built-in features, enabling custom menu commands, tools, and parametric objects:

* **Plugin Types** – There are three primary plugin types in Vectorworks, each saved as a different file type:

  * **Menu Commands (.vsm)** – Scripts that appear as commands in menus. They perform operations on the active document (for example, modifying selected objects or running calculations).
  * **Tools (.vst)** – Scripts that behave as drawing tools on tool palettes. Like native tools, they can accept user clicks/drag input (using the SmartCursor) and can respond to the document’s state (view orientation, selection, etc.).
  * **Parametric Objects (.vso)** – Scripts that define custom **parametric plugin objects** (sometimes called PIOs). These appear as new object types that users can insert into drawings, with parameters editable in the Object Info palette. They act similar to built-in “smart” objects (doors, windows, etc.), supporting snapping, object editing, and parametric regeneration.

* **Parametric Object Subtypes** – Vectorworks defines four subtypes of plugin objects based on how they are placed and edited:

  * *Point objects:* Placed by a single click (plus an optional second click for rotation). Edited via the Object Info palette (cannot be reshaped by drag).
  * *Linear objects:* Placed by two clicks defining a line length/orientation. They display reshape handles at each end for editing, or can be edited in the Object Info palette.
  * *Rectangular objects:* Placed by either corner-to-corner or center-out rectangle drawing (two clicks defining width and height). They have resize handles on the perimeter and Object Info palette parameters (length/width).
  * *Path objects:* Created by a series of clicks defining a polyline (2D path) or NURBS curve (3D path). They can be reshaped with the Reshape tool or via Object Info.

* **Integration and Behavior** – Scripted plugins integrate seamlessly with Vectorworks. When added to a workspace, a plugin menu command or tool is listed alongside native ones. When the user invokes a command or tool, Vectorworks loads the plugin script and executes it. Parametric object plugins, once inserted in the drawing, behave like symbols/objects: they can be copied or exchanged between files, their parameters are shown in Object Info palette, and editing a parameter causes the object’s script to re-run and redraw the object. Plugin objects essentially carry their script with them, so if you share a file with someone, the custom object still works (provided the plugin exists in their Vectorworks or is embedded in the file’s resources).

* **Plugin Architecture** – Under the hood, each plugin consists of your script code plus a plugin “wrapper” that defines its metadata and how it behaves in Vectorworks. The wrapper includes information like the plugin’s type and category (for grouping in the interface), what triggers load (e.g. user action or events), what parameters it has, default values, etc. At runtime, Vectorworks manages plugin activation: for example, a menu command can be set to require a certain selection or view to be active before it runs. Tools automatically benefit from features like SmartCursor feedback. Parametric objects store a **parameter record** for each object instance that holds its parameter values; editing these values triggers the object’s script to regenerate the geometry.

Understanding these fundamentals will inform how we set up and develop plugins in the sections below.

## Environment Setup for Plugin Development

Before writing a plugin, you need to configure Vectorworks and know where to store and test your scripts:

* **Enabling the Plug-in Manager:** Vectorworks 2025 includes a built-in Plug-in Manager (accessible via **Tools > Plug-ins > Plug-in Manager**, or the shortcut **Ctrl+Shift+Z** on Windows). Ensure you have access to this, as it is the primary interface for creating and managing plugins. No special developer license is required for scripting; any Vectorworks installation can run custom VectorScript/Python plugins.

* **User Plug-Ins Folder:** When you create a new plugin, Vectorworks will save it to your user plugins directory. On Windows, the default location is:
  **`C:\Users\<Username>\AppData\Roaming\Nemetschek\Vectorworks\2025\Plug-Ins`**.
  Vectorworks searches this folder (and the application’s own Plug-Ins folder) at launch to register available plugins. Make sure your plugin files (.vsm, .vso, .vst, etc.) reside here (or in a subfolder) so that Vectorworks loads them. By default, the Plug-in Manager will create new plugin files in the correct user folder.

* **Writing and Editing Scripts:** There are two ways to write your plugin’s code:

  1. **Using the Built-in Script Editor:** The Plug-in Manager allows you to create a new plugin and then **Edit Script** to open the Vectorworks Script Editor for that plugin. In the editor, you can write either VectorScript or Python code (you’ll choose the language when creating the plugin). The editor provides a basic environment with syntax highlighting. If writing VectorScript, use the **gear icon (“Compile”)** to compile and catch syntax errors. VectorScript must compile without errors before it can run. Python scripts are interpreted at runtime (no manual compile step), but you can still open/edit them in this editor.
  2. **External Source Files:** You can also maintain your code in an external text file and **include** it in the plugin. The Plug-in Manager has an option to specify an “Include File” for the script (VectorScript uses `.vss` include files; Python uses `.px` files). Using an external file is convenient for using an external code editor or version control. If you go this route, you would update the external `.py` or `.px` file and then reload or restart Vectorworks to test changes. *(Note:* When first creating a plugin via the Plug-in Manager, it will still make a stub plugin file in the user folder. You can then link to your external script.)

* **Testing Plugins:** After writing your code, add the plugin to a Vectorworks workspace to test it:

  * **Menu commands** – Use the Workspace Editor (Tools > Workspaces > Edit Current Workspace) to find your plugin under the chosen **Category** and add it to a menu. (When you created the plugin, you can set a Category for it – e.g., “My Plugins” – so it’s easier to find in the editor.) Once added, you’ll see the new menu item in Vectorworks. Click it to run your script.
  * **Tools** – Similarly, add the custom tool to a tool palette via the Workspace Editor. You might create a new palette for your tools or put it under an existing one. After adding, select the tool in the Vectorworks toolbar and use it like any other drawing tool (e.g. click in the drawing to activate).
  * **Parametric Objects** – For object plugins, adding them to a workspace will make them appear in the *“Objects”* tool palette or under a specific toolset. For example, if you categorized it under “Objects-Plug-in”, it might show in the Building Tools set. Once added, you can select the tool and click in the drawing to insert the object. The object’s default parameters (from your plugin definition) will be used initially, and you can then adjust values in the Object Info palette to see the object update.

  *Tip:* You do **not** need to manually import plugin scripts into documents – once a plugin is in the user Plug-Ins folder and added to the workspace, it’s globally available in Vectorworks for any file.

* **Debugging Techniques:** Debugging plugin scripts can be challenging, especially for Python. Here are some tips:

  * **VectorScript Debugger:** Vectorworks provides a source-level debugger for VectorScript which allows stepping through code, inspecting variables, and setting breakpoints. This can be very helpful for complex scripts. You can enable the VectorScript debugger via the Debug menu in the script editor (available when a VectorScript is open and compiled).
  * **Print and Alerts:** For both Python and VectorScript, a common simple debugging method is to use messages or alerts to output values. For example, `AlrtDialog('Value=' + Num2StrF(x));` in VectorScript or `vs.AlrtDialog(f"Value={x}")` in Python will show a dialog with your variable’s value. You can also use `vs.Message()` to display text in the status bar.
  * **Logging to Text File:** In Python, you can use file I/O to write debug information to a log file on disk (since Python has full file access). This is a way to gather debug info without interrupting the Vectorworks UI.
  * **Error Handling:** If a Python plugin crashes (raises an exception), Vectorworks will typically throw an alert with the error message and stack trace. Use this feedback to locate the issue. In VectorScript, errors might be caught at compile time or might produce alerts at runtime. Always compile your VectorScript and fix syntax errors before running.
  * **Interactive Testing:** For quick experimentation, you can use the *Resource Manager* to create a temporary script (in a Script Palette) and run it. For example, to test a small code snippet (VectorScript or Python) outside of the plugin context, create a document script and run it. This won’t have the plugin’s parameter context, but it’s useful for testing API calls in isolation.

In summary, ensure your plugin files are in the correct folder, use the Plug-in Manager and Workspace Editor to set up your plugin in Vectorworks, and adopt debugging strategies (debugger or log outputs) to troubleshoot issues during development.

## VectorScript vs Python Scripting – Syntax and Capabilities

Vectorworks offers both **VectorScript** and **Python** for scripting, and they each have strengths. Understanding their differences will help you decide which to use (you can mix – e.g., write some plugins in Python and others in VectorScript – they coexist peacefully).

* **Language Origins:** VectorScript is a proprietary scripting language based on **Pascal**. It’s been part of Vectorworks for decades. It uses Pascal-like syntax (strong typing, `Begin/End` blocks, semicolon line endings, etc.) and is **compiled** to bytecode before execution. Python, on the other hand, is a modern, general-purpose language. Vectorworks integrated a Python 3 interpreter (as of Vectorworks 2014 and later) as an alternative to VectorScript. Python scripts in Vectorworks are **interpreted** at runtime (no upfront compilation step).

* **API Access:** Both languages have equal access to the Vectorworks scripting API. In fact, *“VectorScript functions \[are] a library inside of Python”*. This means that anything you can do with VectorScript (creating objects, modifying attributes, querying the document, etc.) can also be done in Python by calling the corresponding function from the `vs` module. For example, the VectorScript procedure `Rect(x, y, x2, y2)` (which draws a rectangle) is available in Python as `vs.Rect(x, y, x2, y2)`. Under the hood, both call the same core functionality in Vectorworks. **Important:** Python can call Vectorworks API functions, but it doesn’t magically gain more powers within Vectorworks than VectorScript has. The advantage of Python is in the language itself and its ecosystem, not in accessing additional Vectorworks-specific features (aside from external libraries).

* **Syntax Differences:** VectorScript’s Pascal heritage means:

  * It’s **case-insensitive** (variables and function names are not case-sensitive).
  * Blocks of code are wrapped in `BEGIN ... END;` instead of indentation.
  * You must declare variables and their types in a `VAR` section.
  * Each statement ends with a semicolon (`;`).
  * It has a classic procedural structure: you typically write a `PROCEDURE MyPlugin; ... BEGIN ... END; RUN(MyPlugin);` for a plugin script. Compilation will catch syntax errors or undefined variables, etc., before you run the code.

  Python, by contrast:

  * Is **case-sensitive** (e.g., `objectHandle` is different from `objecthandle`).
  * Uses indentation (whitespace) to denote blocks instead of `BEGIN/END`.
  * Variables are dynamically typed (no upfront declaration).
  * No need for an explicit `RUN()` call at the end of the script – the Python script just executes top-down when the plugin is invoked.
  * Syntax errors aren’t known until you run the script, and even then only when the interpreter encounters them (so you might hit an error halfway through execution if a line is syntactically wrong or if a name is not defined).

* **Development Experience:**

  * *VectorScript pros:* Being compiled means you catch errors early. The VectorScript **debugger** is a big plus for complex logic. Also, VectorScript has some convenience in Vectorworks like the *“Export Script”* commands (which export drawing elements to VectorScript code automatically). This can generate boilerplate script code for creating certain objects. Many longtime Vectorworks users have a library of VectorScript routines, and the language hasn’t changed much in years (Pascal itself is very stable).
  * *VectorScript cons:* It’s a niche language. Resources for learning Pascal/VectorScript are harder to find (most are older documents). You’re largely limited to what Vectorworks offers; there’s no easy way to use external code libraries in pure VectorScript.
  * *Python pros:* Python is popular and powerful. You have access to a huge range of libraries for tasks like web requests, advanced math (NumPy), XML/JSON processing, etc.. If your plugin needs to interact with external systems or do complex data manipulation, Python is ideal. There are abundant learning resources for Python as well. Python scripts can be more concise due to dynamic typing and not needing verbose `BEGIN/END` blocks.
  * *Python cons:* No integrated debugger in Vectorworks (you rely on print/logging for debugging). Errors at runtime can be harder to trace because you don’t have a compile step to catch issues. Also, Python’s case-sensitivity and whitespace rules require discipline, especially if you’re coming from VectorScript/Pascal which is more forgiving. Another consideration: the Python environment in Vectorworks is **embedded** – meaning it uses a specific Python version (Vectorworks 2025 uses Python 3.9.2 as of this writing) and might not include all Python standard libraries (for example, GUI libraries like Tkinter may not be fully available on all platforms).

* **Interoperability:** While you can’t directly mix VectorScript and Python in the same plugin script, they can work side by side in the *application*. For instance, one plugin can be written in Python and another in VectorScript – they will both run. Vectorworks doesn’t provide a direct way for a running VectorScript to call a Python script or vice versa, but you could use file-based communication or data stored on objects to have them indirectly work together. In general, however, you’ll choose one language per plugin. You can convert existing VectorScript code to Python fairly easily, since the API calls are essentially the same (just with a `vs.` prefix and Python syntax). In fact, if you know VectorScript well, think of Python scripting in Vectorworks as “VectorScript plus extra Python goodness.”

In summary, use **VectorScript** if you prefer a stricter, classic language with debugging support – especially for purely geometry or document-focused plugins. Use **Python** if you need modern language features, external libraries, or are already comfortable with Python. Both will let you accomplish the same tasks within Vectorworks.

## Creating Parametric Plugin Objects (PIOs)

One of the most powerful customizations is to create your own parametric object – a plugin that defines a custom object type with parameters. We’ll cover how to make a simple parametric object plugin step by step.

**1. Define a New Plugin Object:** Open the **Plug-in Manager** (Tools > Plug-ins > Plug-in Manager). In the *Custom Plug-ins* tab, click **New**. In the *Assign Name* dialog, enter a name for your object and select **Object** as the type. You’ll also need to choose the subtype: point, linear, rectangular, or 2D/3D path. For example, choose “Point Object” for a simple object that inserts with one click. Vectorworks will append the appropriate file extension (e.g. “.vso” for objects) to the name. After clicking OK, an empty plugin object is created and added to your user Plug-Ins folder.

**2. Define Object Parameters:** With your new plugin selected in the Plug-in Manager, click **Edit Definition**. This opens the *Edit Plug-in Definition* dialog. Go to the **Parameters** tab. Here you specify what parameters (fields) your object will have, which become editable in the Object Info palette when the object is placed. Add parameters for any adjustable values in your object. Common parameter types include Integer, Real (for dimensions), Boolean (checkbox), Pop-up (list of choices), Text, etc. Each parameter has:

* **Name:** This is the internal name used in your script (also the record field name) – no spaces allowed, typically start with a letter. If you prefix the name with `__` (double underscore), the parameter will be hidden from the user in the OIP (useful for internal data storage).
* **Alternate Name:** The label shown in the Object Info palette (can include spaces or localized text).
* **Type:** Data type (Integer, Real, Boolean, etc., or special types like “Dimension” which is a Real with units).
* **Default Value:** Initial default. Provide something sensible here; for numeric fields, this must be a number (even 0) and not blank.

For example, if you are making a custom “Simple Window” object, you might add parameters: `Width` (Real), `Height` (Real), `FrameThickness` (Real), `Open` (Boolean for open/closed). Each instance placed will carry these values (and you can change them per instance). *Note:* For certain object subtypes, some parameters are auto-created (e.g. a rectangular object auto-generates `LineLength` and `BoxWidth` for the initial rectangle size). You can still add more of your own.

Save the plug-in definition changes. Now your object plugin knows what parameters it has.

**3. Write the Object’s Script:** Back in the Plug-in Manager, with your plugin selected, click **Edit Script**. This opens the code editor. If you created the plugin as a VectorScript object, you’ll write a VectorScript *procedure* here; if Python, a Python script. The script should do whatever drawing or calculations are needed to produce the object’s geometry based on the current parameter values.

Some important notes when scripting plugin objects:

* The script is executed whenever the object needs to regenerate: when it’s inserted, when a parameter changes, or if the object is moved/rotated (Vectorworks may call for regeneration on certain events like file open or layer scale change as well).
* In a VectorScript object script, you can access the parameters directly by using their names prefixed with `P`. For example, if you have a parameter named `Width`, you can use `PWidth` in your code to get its value for the current object. (Behind the scenes, these are pseudo-variables that Vectorworks makes available to your script, pulling from the object's record fields.)
* In a Python object script, you similarly can get parameter values. The easiest way is to use the `vs` module’s attribute: e.g., `val = vs.PWidth`. Newer versions of Vectorworks allow direct access like this (older versions required using `getattr(vs, 'PWidth')` trick). Once you have the parameter values, your Python code can use them in calculations and API calls.
* Always assume your script might run multiple times and should generate the geometry *from scratch* each time (Vectorworks will typically erase the previous geometry of the object before running your code). So your code should create all parts of the object every time it runs (drawing primitives, setting attributes, etc., based solely on the param values and perhaps external state like document units).

For example, let’s create a very simple parametric object: a rectangle whose width and height are set by parameters. We’ll do it in both languages:

**VectorScript (example object script):**

```pascal
PROCEDURE SimpleRectObject;
VAR
    w, h : REAL;
BEGIN
    w := PWidth;    { get the parameter values }
    h := PHeight;
    Rect(0, 0, w, h);   { draw a rectangle from (0,0) to (w,h) }
END;
RUN(SimpleRectObject);
```

**Python (example object script):**

```python
import vs
w = vs.PWidth  # parameter values
h = vs.PHeight
vs.Rect(0, 0, w, h)  # draw rectangle from (0,0) to (w,h)
```

In both cases, assume you defined `Width` and `Height` as Real parameters in the plugin definition. The above scripts draw a rectangle. If you insert this object in the drawing, you would click once to place the point object (the point (0,0) in the script corresponds to the insertion point), and the rectangle will extend out to `(Width, Height)` in local coordinates. Changing the Width or Height in the Object Info palette will cause Vectorworks to rerun the script with the new values, redrawing the rectangle at the new size.

You can, of course, create much more complex geometry: multiple shapes, 3D objects, etc., using any Vectorworks drawing routine (e.g., `vs.Line`, `vs.Circle`, `vs.Extrude`, etc.). Use the parameter values and possibly relationships between them in your calculations. For instance, you might ensure a minimum frame thickness, or calculate additional internal points.

* *Coordinate systems:* Plugin object scripts work in the object’s **local coordinate system**, where `(0,0)` is the insertion point of the object. If the object is rotated or moved, Vectorworks handles that externally; your script typically doesn’t need to know the world coordinates of where it’s placed. Draw everything relative to `(0,0)` or relative to each other. If you need the object’s location in the world (less common), there are API calls to get the object’s transform or location.

* *Object Info Palette display:* The values of parameters show up in the OIP automatically. If you want to update a parameter programmatically (e.g., set a default based on another), you can use calls like `vs.SetRField` (to set the object’s record field for that parameter) – but be careful, doing so may trigger recursive resets. It’s usually best to let the user input drive the parameters, except in *event-enabled* scenarios (discussed later) where you handle button clicks or other interactions.

**4. Adding the Plugin to the Workspace:** After writing and saving the script, close the editor. Now add your new object to a workspace so you can use it. Go to **Tools > Workspaces > Edit** (or Manage Workspaces) and find your plugin under the category you chose. Place it in an appropriate tool palette. For example, you might create a new palette called “Custom Objects” and add it there. Save the workspace. Now your tool should appear in the Vectorworks UI. Select it, then click in the drawing to insert your object. It will run the script and draw whatever you programmed (our rectangle, for example). The Object Info palette will show the parameters you defined (Width, Height, etc.) which you can edit, and the object will update immediately.

**5. Persisting Default Values:** Each plugin object has default parameter values that are stored in the *file’s* resources once the plugin is used. For instance, when you first use your object in a new file, Vectorworks creates a default param record in that file with the plugin’s default values. If you change a parameter on one instance and then use the **Create Similar Object** command or insert a new instance, Vectorworks might carry over last-used values. This is convenient for the user. Just be aware that the “Defaults” for your object in any given file can evolve. You can always reset defaults in that file by editing the param values of a fresh instance and using the “Replace Defaults” button (if available). This mechanism is automatic; your script doesn’t typically manage it. But do note that switching files will use the defaults of that file. If no defaults exist (object not used before in that file), it uses the defaults from your plugin definition.

**6. Using Dialogs or Custom UI in Objects:** By design, parametric objects are primarily controlled via the Object Info palette (OIP) fields. However, you might want a more complex UI – for example a button that opens a configuration dialog, or dynamically show/hide certain parameters. This is possible with **event-enabled objects** (discussed in detail in a later section). In short, you can declare your object “Event Enabled” in the plugin Properties, and then within your script handle various events like OIP widget interactions. Through the event system, you can create OIP controls such as buttons, static text, separators, images, etc., beyond the basic parameters. When the user clicks a button in OIP, your script gets an event and you can respond (e.g., by showing a custom dialog using `vs.CreateLayout` and related functions). Implementing custom dialogs involves using the Vectorworks Dialog API (which is available to both VectorScript and Python). For example, you can use `vs.CreateLayout` to define a dialog layout with controls, then `vs.RunLayoutDialog` to display it and capture input. Covering the full dialog API is outside the scope of this guide (it’s quite extensive), but Vectorworks’ Function Reference has all the details, and the community forums have examples. Many plugin developers start by using simple `vs.AlrtDialog` prompts or `vs.StrDialog` (which prompts for a text input) for quick input needs, then move to custom dialogs as needed for more complex interactions.

By following these steps, you can create a wide range of custom objects – from simple shapes to complex multi-component objects. Always test your object thoroughly: insert it, change parameters, duplicate it, rotate it, try it in new documents – to ensure the script handles various scenarios without errors.

## Creating Custom Tools and Menu Commands

In addition to objects, Vectorworks lets you create custom **menu commands** and **tools** via scripting. The process is similar (define a plugin, write a script), but the behavior and use-cases differ. Let’s break down each:

### Menu Commands (Plug-in Commands)

A menu command plugin is essentially a script that runs on-demand when the user selects it from a menu (or presses a shortcut). It does not have persistent geometry of its own (unlike an object) – it just performs an action and finishes.

**Typical uses:** automating a task (e.g., renaming classes, batch editing objects, exporting data), running a custom calculation or modification on the drawing, etc.

**Creating a Menu Command:** In the Plug-in Manager, create a **Command** type plugin (extension `.vsm`). Give it a name (this will also be the menu text unless you localize it) and a category. After creating it, define any needed **default parameters** if you want to store settings between uses (menu commands can have a parameter record too, for remembering user choices from last run) – though many simple commands won’t need any parameters (besides maybe hidden ones for internal use).

Now **Edit Script** to write the code. A menu command script executes once when the command is chosen. There is no automatic context like an insertion point or object – however, the script can query the state of the document, selection, etc., and act accordingly.

For example, a menu script might check “is there a selection? If so, operate on selected objects, otherwise alert the user.” You can use functions like `vs.Count(`*criteria*`)` or selection iteration to determine that. Vectorworks allows you to specify, in the plugin definition, certain conditions for menu commands such as “Requires a selection” or “Only available in 3D views,” etc., which will automatically disable the menu item if conditions aren’t met. You set these in the plugin’s properties (there are checkboxes for modes like “Needs Plan View” or “Needs Selection”). These are optional but good for user experience.

Writing the script is straightforward procedural code. Here’s an example of a simple menu command in both languages:

**VectorScript (example menu command):**

```pascal
PROCEDURE HelloCommand;
BEGIN
    AlrtDialog('Hello, Vectorworks user!');
END;
RUN(HelloCommand);
```

This VectorScript simply pops up an alert dialog with a greeting. It doesn’t use any document context – it’s just a trivial example of a command that produces an output.

**Python (example menu command):**

```python
import vs
vs.AlrtDialog('Hello, Vectorworks user!')
```

Equally simple – it calls the Vectorworks alert dialog function via the `vs` API.

Of course, commands can be much more useful. For instance, you might write a command to take all selected objects and distribute them evenly along the X-axis. In Python pseudocode that might look like:

```python
import vs
objs = []
h = vs.FSActLayer()  # first selected object
while h:
    objs.append(h)
    h = vs.NextSObj(h)
if len(objs) < 2:
    vs.AlrtDialog('Select at least 2 objects.')
else:
    # Compute spacing and move objects
    objs.sort(key=lambda o: vs.GetBoundingBox(o)[0])  # sort by x position
    x0 = vs.GetBoundingBox(objs[0])[0]
    xN = vs.GetBoundingBox(objs[-1])[0]
    spacing = (xN - x0) / (len(objs)-1)
    for i, obj in enumerate(objs):
        vs.HMove(obj, x0 + i*spacing - vs.GetBoundingBox(obj)[0], 0)
```

*(This is a conceptual example for distributing objects horizontally – not guaranteed to be complete, but illustrative.)* The script gets selected objects, computes an even spacing, and moves them. A VectorScript equivalent could be written using `FOR EACH` and `HMove` similarly.

After writing your command script, **add the command to a menu** via the Workspace Editor (e.g., under a “Commands” menu or a custom menu). Then run it to test. If it’s something that alters objects or the document, verify it behaves as expected (and ideally, handle error cases or no-selection cases gracefully with messages).

### Tool Plug-ins

A tool plugin allows you to create a custom tool that interacts with the drawing area, typically for creating or manipulating objects through user clicks or drags – similar to built-in drawing tools. Examples: a tool that draws a special kind of line with certain attributes, or a tool that lets the user pick points and then creates a custom object (like a polyline generator with specific properties).

**Creating a Tool:** In Plug-in Manager, create a **Tool** type plugin (extension `.vst`). When you create a tool, you have some additional options in the plugin definition: tools can have modes and preferences. For example, you might give your tool a parameter for “Mode” that can be a pop-up menu (like how the Polyline tool has corner modes, etc.), or checkboxes for options. These become tool default parameters (accessible via double-clicking the tool or via a preferences dialog automatically if you check “Show Preferences” option). Define any parameters your tool needs in the Parameters tab (just like with objects). Commonly, tools might have parameters to store last-used values (like a default radius or an option toggle). If you don’t need any, that’s fine too.

**Tool Script Basics:** A tool script runs in a loop reacting to user input. In VectorScript, historically, you’d use functions like `GetPt` to prompt the user for points, or `TrackObject` to handle dragging, etc., within the script. In Python, similarly you can call `vs.GetPt()` or other input functions. However, when writing a plugin *tool*, there is a more advanced mechanism: you can make the tool event-enabled (like object events, there are tool events) and use a state machine approach. That is more complex, so for many simple tools the straightforward approach is:

* Prompt user for necessary clicks using `vs.GetPt`, `vs.GetPtL` (get point and rubber-band line), or `vs.GetRect` (two points), etc.
* After gathering input, create or manipulate objects accordingly.

**Important:** Many interactive calls like `GetPt` will **not work** inside an event-driven tool without additional setup (Vectorworks has separate routines for event-enabled tools such as `vs.vstGetPt2D` for getting points during tool events). For simplicity, if your tool is simple, you might choose *not* to mark it event-enabled, and just use a linear script with `GetPt` calls. This will work, but it means the tool isn’t as flexible (for example, you can’t easily provide multiple modes or dynamic cursor feedback beyond basic rubber-banding). It’s a trade-off: ease of coding vs. complexity.

Let’s consider a basic example: a tool that lets the user draw a line between two clicked points (essentially a custom line-drawing tool).

**VectorScript (example tool):**

```pascal
PROCEDURE TwoPointLineTool;
VAR
    x1, y1, x2, y2: REAL;
BEGIN
    GetPt(x1, y1);            { Wait for first click }
    GetPt(x2, y2);            { Wait for second click }
    MoveTo(x1, y1);
    LineTo(x2, y2);
END;
RUN(TwoPointLineTool);
```

When this tool is activated, Vectorworks will change the cursor and wait for the user’s first click (`GetPt` halts script execution until a point is clicked), then the second. After two points, it draws a line. (Note: This example doesn’t include any error-checking; the user could press Esc to cancel, etc., which would abort the script.)

**Python (example tool):**

```python
import vs
(x1, y1) = vs.GetPt()    # get first point
(x2, y2) = vs.GetPt()    # get second point
vs.MoveTo(x1, y1)
vs.LineTo(x2, y2)
```

This does the same thing.

After writing, add the tool to your workspace (e.g., in a “Drafting Tools” palette). When you activate the tool, you’ll notice Vectorworks enters a tool mode (like any line tool) – you click two points and a line appears.

For more advanced tools, you might want multiple clicks or to allow pressing Enter to end input, etc. This can be accomplished by looping `GetPt` or using `GetPoly` for multiple points. If you mark the tool as **event-enabled**, you would handle events such as “point obtained” and “tool terminated” in a more formal way with `vs.vstGetEventInfo`. Event-enabled tools also allow mode groups (buttons in the mode bar) via calls like `vs.vstAddMode` or `vs.SetToolProperty` to configure how many points or clicks to expect. For instance, a rectangular pick tool might have a mode for center-out vs. corner-to-corner placement – you’d implement that by reading a parameter or mode value.

**Using Selected Objects in Tools:** Some tools operate on existing objects (like the Reshape tool operates on a selected object’s geometry). If your tool needs a pre-selection, you can check for selected objects via script (e.g., use `vs.FirstSelectedObject()` at the start). You can also specify in the plugin definition that the tool requires a selection to activate, which will prevent it from being used otherwise (ensuring your script can safely assume something is selected).

**Tool Parameters and Preferences:** If you gave your tool any parameters (say an “option” or default distance), those appear in the Plug-in Manager and can be accessible via OIP *when the tool’s preferences are opened*. For example, if the user double-clicks the tool icon, Vectorworks automatically opens a small dialog listing the tool’s parameters for adjustment. This is handy for tool default settings (just like the built-in tools have a preferences dialog). In your script, you can access those parameter values via `P` variables (VectorScript) or `vs.PParameterName` (Python) similar to objects. They persist between uses of the tool (stored as default in the document or user prefs).

**Example Use-Case:** Suppose you want a tool that draws a circle of a fixed radius every time you click (like a “stamp” tool). You could create a tool plugin with a parameter “Radius”. The tool script would do:

* Read `Radius` param.
* On each click (GetPt), draw a circle at that point with the given radius.
* (Possibly loop for multiple placements until the user hits Esc or right-click to end – or just one placement per activation.)

This tool would allow the user to pre-set the radius via the tool’s preferences. Each time they click in the drawing, a circle is created.

**Summary:** Menu commands and tools extend what you can do interactively:

* Use a **menu command plugin** for one-off actions or batch operations that don’t require interactive drawing. They can present dialogs, process data, and so on.
* Use a **tool plugin** when you want to create a new drawing tool or editing tool that involves user clicks or drags in the drawing area.

Both are scripted similarly, but tools have the added complexity of user input handling. Always test your menu commands and tools carefully (especially tools – test clicking, double-clicking, Esc key, etc., to ensure the script handles interrupts gracefully). Provide user feedback where appropriate (for example, change the cursor using `vs.SetCursor` or display a message in the status bar using `vs.StatusAlert` to guide the user during tool operation).

## Event-Based Plugins (Event-Enabled Scripting)

Vectorworks provides an event-driven model for plugins that require more interactive or dynamic behavior. A plugin (object, menu, or tool) can be marked as **Event Enabled** in its definition. This means that instead of running straight through top-to-bottom, the script can respond to specific events or messages sent by Vectorworks. This is an advanced topic, primarily useful for **parametric objects** and some tools.

For **parametric objects**, event-enabled scripting allows you to create custom user interface elements in the Object Info palette and handle user actions like pressing buttons or changing a dropdown. For example, you might have a parametric object with a “Settings…” button in the OIP – clicking it could bring up a custom dialog to configure the object. Or you may want to dynamically show/hide certain parameters based on a checkbox selection. These things require handling events.

**How to Enable Events:** In the Plug-in Manager, when editing your plugin’s definition, there is usually an **Options** or **Properties** section. For objects, you’ll see a checkbox like “Event Enabled Plug-in” or “Enable event handling”. Check this to turn on event messaging for that object. (For tools, a similar option exists.) Additionally, for object events, you often set the *Reset Event Options* – for example, you can choose to have the object script run on object movement or rotation, etc., if needed. Once events are enabled and saved, your script can use the event-aware functions.

**Event Loop in Script:** Instead of a simple create-geometry script, an event-enabled object script typically has a structure like:

```python
import vs
def execute():
    # Main entry point for events
    theEvent, msg = vs.vsoGetEventInfo()
    if theEvent == vs.kObjOnInitXProperties:
        # Setup code: define custom UI widgets in OIP
        vs.SetObjPropVS(vs.kObjXPropHasUIOverride, True)
        # e.g., add a button:
        vs.vsoAppendWidget(vs.kWidgetButton, kWidgetID_Button1, "My Button", 0)
        # (also define other widgets or properties)
    elif theEvent == vs.kObjOnWidgetPrep:
        # Runs when OIP is being built for this object instance
        # We can enable/disable or show/hide widgets here based on current parameters
        pass
    elif theEvent == vs.kObjOnObjectUIButtonHit:
        # Handle button clicks in the OIP
        buttonID = msg
        if buttonID == kWidgetID_Button1:
            # The user clicked "My Button"
            vs.AlrtDialog("Button was pressed!")
    else:
        # Default behavior (e.g., reset event)
        # Regenerate geometry here:
        width = vs.PWidth
        height = vs.PHeight
        vs.Rect(0,0, width, height)
```

The above is conceptual Python pseudocode for an event-enabled object. The `vs.vsoGetEventInfo()` function tells you what event is being handled. There are constants like `kObjOnInitXProperties` (time to define UI), `kObjOnWidgetPrep` (time to configure UI before display), `kObjOnObjectUIButtonHit` (an OIP button was clicked, with the message giving the widget ID), and the “default” event which is typically the object reset (i.e., time to draw the object geometry). In VectorScript, the structure is similar: you use `GetEventInfo(event, message)` and a `CASE` statement on `event`.

**Use Cases for Events in Objects:**

* **Custom OIP Widgets:** Add buttons, separators, text, images, pop-up dialogs, etc., to create a richer interface. For example, a window object might have a “Flip Handing” button that, when clicked, swaps left/right parameters internally.
* **Conditional Parameters:** Show or hide certain parameters. E.g., if a checkbox “Use Custom Color” is false, hide the color selection parameter; if true, show it. In the `WidgetPrep` event, you can call `vs.vsoSetEventResult(-8)` etc., to hide or disable particular parameters or widgets, based on conditions.
* **External Triggers:** Event-enabled objects can respond to more than just UI. They can catch when the object is moved or duplicated, etc., if you set those notifications. This is niche, but for example, you could have an object that maintains a relationship with another object – you might need to know if it’s been duplicated to also duplicate a linked object (though such complex interactions often suggest using the SDK or a data tag approach).

For **tools**, making them event-enabled allows you to handle each click or move in a loop of events (like a state machine). Vectorworks essentially calls your tool script on events like “mouse down,” “mouse move,” etc., and you respond accordingly (e.g., draw temporary preview, then on completion create the object). The constants for tool events (like `kToolOnMouseDown`, etc.) are different, and you use `vs.vstGetEventInfo()` in a tool. This is beyond the scope of this intro, but the Vectorworks developer documentation has examples of event-enabled tools (for instance, a tool that draws custom geometry with multiple clicks can be managed with these events rather than using blocking `GetPt` calls).

**Example Event Workflow:** Let’s illustrate a simpler scenario for an object:

* Suppose we have an object with a numeric parameter “Count” and we want a button “Increment” in the OIP that, when pressed, will add 1 to Count (just as a trivial example of a dynamic UI interaction).

  * In `kObjOnInitXProperties`: we would add a button widget labeled “Increment”.
  * In `kObjOnObjectUIButtonHit`: if `msg` matches our button’s ID, we would do something like `current = vs.PCount; vs.SetRField(objectHandle, pluginName, 'Count', str(current+1)); vs.ResetObject(objectHandle)` to update the parameter and regenerate the object. (You obtain `objectHandle` via `vs.GetCustomObjectInfo()` at the script start, which gives you the handle to self, definition handle, and record handle.)
  * In the default event (reset), our code would then create geometry according to the current Count (for example, draw that many copies of a shape).

  This way, clicking the button effectively changes a parameter and forces a redraw.

One must consult the Vectorworks Function Reference or sample code for the exact function calls and constants – event-enabled scripting is more complex and has a steeper learning curve. It’s often used for developing professional-grade plugins with polished UIs. If you’re just starting, consider if you really need event handling, or if a simpler approach (like an external dialog invoked by a separate menu command) could suffice. But it’s good to know this capability exists.

**Summary of Event-Based Plugin Advantages:**

* Create interactive UI elements for plugins (especially parametric objects).
* Greater control over plugin behavior in response to user actions.
* Ability to maintain internal state and respond to Vectorworks actions beyond simple execution.

**Note:** With great power comes responsibility – event-driven scripts can be harder to debug. You need to handle sequences of events and maintain state between them (often by storing data in hidden parameters or static variables). Always test event-enabled plugins thoroughly. The community forums have many Q\&As and examples on event-enabled scripting, and the Vectorworks developer wiki provides templates (e.g., *“Python Sample Point Object (complex)”* which demonstrates an event-enabled object with custom UI).

## Advanced Topics

Moving beyond the basics, here are some advanced considerations for Vectorworks plugin development:

### Using External Python Libraries

One huge benefit of Python scripting is the ability to leverage external libraries (for tasks like data analysis with Pandas, communicating with web APIs, etc.). However, since Vectorworks uses an embedded Python interpreter, you can’t directly use pip on your system and expect Vectorworks to see those packages. Instead, you have a couple of options:

* **Manual Installation to “Python Externals”:** Vectorworks has a designated folder for external Python packages. On Windows, it’s typically under your user folder, e.g.,
  `C:\Users\<Username>\AppData\Roaming\Nemetschek\Vectorworks\2025\Python Externals\`
  If you have a `.whl` (wheel) or package, you can install it into this folder. One method is using pip with a target: e.g., running in a command prompt `pip install --target="C:\Users\<User>\AppData\Roaming\Nemetschek\Vectorworks\2025\Python Externals" packagename`. This will place the library in the folder where Vectorworks looks. You need to restart Vectorworks afterwards.
* **Marionette.VerifyOrGetLib**: Vectorworks’ Marionette library includes a function `VerifyOrGetLib(packageName, url)` that some have used to automate library installation in a script. Essentially, you provide it the URL of a wheel file; when run, it will prompt the user and then fetch and pip-install that wheel into the Python Externals folder (it actually spawns a pip subprocess). This is a user-friendly way to ensure a needed library is present. For example, a script could attempt `import numpy`, catch ImportError, then use `Marionette.VerifyOrGetLib("numpy", "<url-to-numpy.whl>")` to get it. Keep in mind this requires internet access from the user’s machine and will ask the user for permission (a dialog appears).
* **Bundling Libraries with Plugins:** If the library is pure Python and not too large, you could bundle it within your plugin (e.g., include the .py files or a .zip in the plugin file structure). This can be done by copying the library into your plugin’s folder and adjusting `sys.path` in your script to include it. Vectorworks does allow plugin distributors to include auxiliary files. For instance, a .vsm could be distributed as a .zip with additional Python modules. The user would install it via the Plug-in Manager’s “Install” button (which accepts a .zip and places files appropriately).
* **Python Version Compatibility:** Note that Vectorworks 2025 uses Python 3.9. Make sure any library you attempt to use is compatible with Python 3.9. Also, if a library has C extensions, you need a wheel built for Python 3.9 and the correct architecture (e.g., Windows 64-bit). If no wheel is available, you might not be able to use that library unless you compile it for the Vectorworks environment.

Using external libraries can greatly extend what your plugin can do – from reading Excel files (with openpyxl) to performing complex calculations. Just plan for the deployment: if sharing your plugin with others, you must also share instructions or means to install the required libraries. The **Vectorworks Developer page “Python Package Catalog”** lists some packages and the Python version they correspond to, which might be a helpful reference.

### Managing Persistent Data and User Preferences

Sometimes a plugin needs to remember information between runs or between Vectorworks sessions. We discussed one method: using plugin parameters (especially for tools/commands, which can store last-used values in their parameter record). But what about data that is not a simple parameter?

Options for persistent data:

* **SavedSettings (Vectorworks Preferences):** Vectorworks provides a key–value storage in the user’s preferences file via `vs.SetSavedSetting(category, key, value)` and `vs.GetSavedSetting(category, key)`. This is like writing to a config file. For example, your plugin could save a user’s preferred default directory or an API token using `vs.SetSavedSetting('MyPlugin', 'ApiToken', tokenValue)`. These settings persist across sessions (they are stored and loaded next time Vectorworks starts). Use a unique category string for your plugin to avoid conflicts. Values are stored as strings (so you may need to serialize more complex data, or store multiple keys).
* **Hidden Parameters:** In a parametric object, you can include parameters that are hidden (`__` prefix in name) to store extra info per object. For example, an object could store a GUID or a timestamp as a hidden param. This persists with the object in the file. This is per-object persistence rather than global user preference.
* **External Files:** Your plugin (especially if Python) can write to external files (like a JSON config in the user’s Documents or AppData). For instance, you might save a JSON of user preferences or cache data in a known location. Just be mindful of cleanup and informing the user if needed.
* **Document Data:** You can also store data in the VWX file itself via custom records or fields on invisible objects. This is rarely needed unless you need to embed configuration that travels with the file. But one could, for instance, have a hidden text node on layer none that stores some JSON in a hidden record – a bit hacky, but it’s an approach.

For most cases, `SetSavedSetting` and `GetSavedSetting` are easiest for small bits of data across sessions (like remembering the last folder used, etc.) – they act like application-level preferences for your scripts.

### Distributing and Installing Plugins

If you develop a plugin for others to use, consider how to package it:

* The **Plug-in Manager** has an *Install* feature (in the Third-party Plug-ins tab) that allows users to install a plugin from a zip file. The typical distribution is a **zip file** containing your plugin files. For example, if you wrote `MyTool.vst` and perhaps an external `MyTool.py`, and maybe a custom icon, you would zip these into `MyTool.zip`. The user clicks Install in their Plug-in Manager, selects this zip, and Vectorworks will unzip it into their user Plug-Ins folder automatically. (They will need to restart Vectorworks to load it, as noted.)
* If your plugin consists of a single file (like just a .vsm with embedded code), you can also distribute that file and instruct users to put it in their Plug-Ins folder manually. However, using the Install method is more convenient especially if multiple files.
* You can provide instructions in a README or an installer. Some developers even create Vectorworks “vwr” (resource) files or use Vectorworks Package Manager, but those are typically for larger-scale distributions.
* If your plugin should be accessible in the workspace, you may also share instructions for adding it to the workspace (the user has to do this step themselves unless you supply a custom workspace or an installer that automates it).
* **Icons:** You can assign a custom icon to your tool or command. This is done by placing a PNG file with the same base name as the plugin (and maybe specific size suffix – check Vectorworks documentation) in the user Plug-Ins folder. For example, `MyTool.vst` could use an icon file `MyTool.png`. Vectorworks will use that in the workspace (usually 20x20 pixel icons). Details on icon naming and sizes are in developer docs.
* **Obfuscation/Encryption:** If you intend to distribute your plugin but protect the source code, Vectorworks allows you to encrypt plugins. An encrypted plugin cannot be edited by users. You would use Vectorworks Plug-in Manager’s **Encrypt** feature (or export plugin as encrypted). This produces .vxo (for objects) or .vxt/.vxm files etc. corresponding to the encrypted versions. Only do this when you’re ready to distribute and want to keep code private – otherwise, for open sharing, you can leave it unobfuscated so others can learn from or modify it.

Lastly, include documentation or comments in your code for users (and for yourself, for maintenance). If you have multiple plugins that work together, make sure to test them in a clean environment (maybe on another machine or a fresh user folder) to ensure you included everything needed.

### Performance Considerations

As your plugins get more complex, be mindful of performance:

* VectorScript and Python API calls into Vectorworks are generally fast for single operations, but if you, say, loop over thousands of objects, it can become slow. Use criteria-based functions (`ForEachObject` with a criteria, or `vs.ForEachObject` in Python) to let Vectorworks handle iteration in native code where possible – it’s faster than doing Python loops that call back into VW thousands of times.
* For parametric objects, try to minimize unnecessary regeneration. Don’t mark the object to reset on every minor change unless needed. Avoid overly complex geometry calculations on the fly.
* Use caching if appropriate. For example, if on every reset you perform a heavy calculation that depends on some parameter, and that parameter hasn’t changed since last time, you could store the result in a hidden parameter to reuse. However, weigh this complexity unless you truly face performance problems.

### SDK vs Scripting

For completeness: extremely advanced plugins (or those needing capabilities beyond what scripting offers) can be developed with the Vectorworks SDK (C++). The SDK allows deeper integration but requires C++ knowledge and compiling DLLs. The majority of typical automation and custom object needs can be met with VectorScript/Python, but if you ever hit a wall, the SDK is the next step. The Vectorworks Developer community and documentation can guide you there, but that’s outside our scope here.

## Code Examples for Common Tasks

Below are some additional code snippets demonstrating common plugin tasks in both VectorScript and Python. These illustrate patterns you might reuse in your own plugins:

* **Looping Through Selected Objects:** For a menu command that operates on whatever the user has selected, you often need to loop through selected objects.

  * *VectorScript:*

    ```pascal
    PROCEDURE DoSomethingSelected;
    VAR
      h : HANDLE;
    BEGIN
      h := FSActLayer;  { first selected object on active layer }
      WHILE (h <> NIL) DO BEGIN
        { perform an action on h, e.g., change its color }
        SetPenFore(h, 65000, 0, 0);  { set pen color to red (RGB) }
        h := NextSObj(h);  { get next selected object }
      END;
    END;
    RUN(DoSomethingSelected);
    ```

    This goes through all selected objects and sets their pen color to red.
  * *Python:*

    ```python
    import vs
    h = vs.FSActLayer()  # first selected handle
    while h:
        # e.g., set each selected object to red pen
        vs.SetPenFore(h, 65000, 0, 0)
        h = vs.NextSObj(h)
    ```

    The logic is the same. We use the Vectorworks API call `NextSObj` (next selected object) to iterate.

* **Getting/Setting Object Parameters (Record Fields):** If you want to fetch or change data on objects (other than plugin params), you often use record fields.

  * In VectorScript, `GetRField(objHandle, recordName, fieldName)` and `SetRField(objHandle, recordName, fieldName, value)` are used.
  * In Python, the same via `vs.GetRField` and `vs.SetRField`.
    Example: get the `Layer` field of a Lighting Device (Spotlight object):

    ```python
    import vs
    lightingObj = vs.FSActLayer()
    if lightingObj:
        layerName = vs.GetRField(lightingObj, "Lighting Device", "Layer")
        vs.AlrtDialog(f"Lighting device layer is {layerName}")
    ```

* **User Input via Dialogs:** The simplest user input in a script (without building a full dialog layout) is:

  * `vs.AlrtDialog("Message")` – display a message (user clicks OK).
  * `vs.StrDialog("Prompt", default)` – prompt user to enter a text string.
  * `vs.RealDialog("Prompt", defaultStr)` – prompt for a numeric value (returns a string, which you’d convert to number).
  * `vs.YNDialog("Question")` – yes/no question (returns 1 for Yes, 2 for No, 3 for Cancel).

  VectorScript has equivalent procedures `AlrtDialog`, `StrDialog`, etc. These are modal dialogs useful for simple input without making a full custom dialog.

* **Creating Geometry:** Both languages use the same drawing functions. Some commonly used ones:

  * `MoveTo(x,y)` / `LineTo(x,y)` – start a path at (x,y) and draw line.
  * `Rect(x1, y1, x2, y2)` – draw rectangle by opposite corners.
  * `Oval(x1, y1, x2, y2)` – draw an oval inscribed in the rectangle defined by those corners (if that rectangle is a square, you get a circle).
  * `Arc(centerX, centerY, startAngle, sweepAngle, radius)` or similar – draw arcs.
  * `vs.Locus(x,y)` – place a locus point (reference point).
  * `vs.HDuplicate(obj, dx, dy)` – duplicate an object by offset.
  * `vs.Symbol(symName, x, y, angle)` – insert a symbol instance.
  * `vs.CreateText(text)` – create a text object with given content.
  * 3D: `vs.Extrude(obj, height)` – extrude a 2D object.
  * `vs.AddSolid(obj1, obj2)` – boolean add solids, etc.

  These can all be used inside scripts. Just remember for parametric objects, use local coordinates. For tools/menu commands, if you need world coordinates, you may convert or get working plane info if needed.

* **Calculations and Units:** Vectorworks stores lengths in document units (in VectorScript, a REAL is typically document units). If you need to convert, there are functions like `vs.Distance(x1,y1, x2,y2)` to get distance, `vs.Angle(x1,y1,x2,y2)` to get angle between points, etc. If dealing with unit strings, `vs.ValidNumStr` can parse a user-input string with units into a numeric value (e.g., user types "5cm" – it can convert that to document unit value).

The key to mastering plugin scripting is to leverage the **Vectorworks Function Reference** (for all available functions/procedures). It’s available on the developer site and also in the local help (offline) – on Windows, you can find a “VWScript Reference.html” that lists everything, or use the online developer wiki. When stuck, search for what you want to do; e.g., “VS\:Circle” or “VS\:CreateDialog” on the developer site.

## Resources and Documentation

Finally, to deepen your knowledge and keep updated:

* **Official Vectorworks Developer Documentation:** The developer portal  is a treasure trove. In particular:

  * *Function Reference* – detailed reference for all VectorScript/Python API calls (look for “VS Function Reference”).
  * *VectorScript Language Guide* – although a bit older, this PDF (available on the developer site) provides an in-depth look at VectorScript’s syntax and examples.
  * *Sample Code and SDK Examples* – useful even if you stick to scripting; they illustrate patterns of plugin development.
  * The site’s search (developer.vectorworks.net) can find pages like “VS\:SomeFunction” or examples contributed by users.

* **Vectorworks Help (User Manual):** The Vectorworks help system (app-help.vectorworks.net for 2025) has a **Scripting** section with basics. It covers how to use script palettes, the Plug-in Manager, and introduces Marionette and scripting. It’s more high-level but good for understanding how scripting fits in the workflow. Specific pages like *“Creating Scripted Plug-ins”* and *“Scripted Plug-in Objects”* are directly relevant.

* **Vectorworks Community Forum:** This is arguably one of the best resources. The **Vectorscript** and **Python Scripting** sections of the forum have many experienced users and NV staff participating. You’ll find Q\&A threads, code snippets, and discussions of tricky issues (e.g., event-enabled scripting quirks). For example, forum posts by users like *Pat Stanford* or *Jesse Cogswell* often contain insightful explanations and sample code. If you encounter a problem, search the forum – chances are someone has asked a similar question.

* **Vectorworks University:** Vectorworks offers online training including scripting courses. There’s a Vectorworks University course on VectorScript basics, and possibly Python as well, which can be useful if you prefer a guided learning approach (videos, exercises).

* **Community Examples and Plugins:** Sometimes examining how existing third-party plugins work is helpful. Some developers open-source their plugins or share code on GitHub or Bitbucket. For example, *Dieter @ DWorks* had a DLibrary for Vectorworks Python to simplify certain tasks. Searching online (GitHub, etc.) for “Vectorworks Python plugin” might yield some repositories. Just ensure any code you copy is compatible with the Vectorworks version and environment.

* **Nemetschek Vectorworks SDK Support:** If you venture into very advanced territory or SDK, the developer forum and dev support at Vectorworks, Inc. can assist. They also maintain a tech bulletin forum for announcing changes (for example, they might post about new Vectorworks 2025 scripting changes or deprecations).

Staying updated: Vectorworks tends to add new functions or improve things each version. For instance, if 2025 introduced new script functions or changed Python versions, it would be noted in the release notes or developer notes. Keep an eye on those when upgrading your plugins to a new VW version.

This guide should give you a solid foundation for building plugins in Vectorworks 2025 using VectorScript and Python. Happy scripting, and good luck extending Vectorworks to fit your unique needs!

**Sources:**

* Vectorworks 2025 Online Help – Scripting Overview and Plug-in Concepts
* Vectorworks Developer Wiki and Function Reference
* Vectorworks Community Forum – expert discussions on VectorScript vs Python, event-enabled plugins, and more.
