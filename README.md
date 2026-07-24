# Blue Wing – SMB3 Editor

Blue Wing is a profile-driven ROM-editing environment for the NES version of *Super Mario Bros. 3*. It brings project management, metadata editing, text editing, palette work, backups, and debugging together in one focused application.

Every SMB3 hack can have its own structure, offsets, features, and creative ambitions. Blue Wing is designed to embrace those differences—and to grow alongside the people building them.

## Main Features

1. **Project Profiles**

   Create, duplicate, activate, and manage JSON-based profiles for different SMB3 projects. Each profile can define its own ROM offsets, available features, editor behavior, backup regions, and stored project data.

2. **ROM Data Preservation**

   Save important ROM data inside a project profile, including (1-2 demand Overworld Names Patch installed):

   1. World banner text and positions
   2. Level names
   3. Level-name palettes
   4. World-map palettes
   5. Custom game text

   Saved profile data can be restored when loading a freshly compiled ROM, helping repeated builds remain consistent.

3. **World and Level Name Editing** (requires patch)

   Edit level names across multiple worlds, customize world banners, control banner placement, and assign map tiles used by level-name triggers.

4. **Palette Editing**

   Adjust world-map and level-name palettes through a visual color interface. Large color swatches and hexadecimal values make it easier to understand and refine each selection.

5. **Game Text Editing**

   Configure and edit supported in-game text, including:

   1. Throne room speeches
   2. Princess letters
   3. Princess rescue dialogue
   4. Toad House messages
   5. Additional profile-defined text entries

6. **Level Backups**

   Back up and restore configured level-data regions individually or all at once. Backups are organized by profile so several projects can be developed without mixing their data.

7. **Flexible ROM Workflow**

   Blue Wing supports the everyday rhythm of ROM-hack development:

   1. Open, save, and save-as operations
   2. Recently opened ROMs
   3. Optional automatic reloading after external builds
   4. Optional automatic saving
   5. Overwrite confirmation
   6. Project-to-profile associations

8. **Debugging and Feedback**

   Inspect ROM addresses, pointers, tile offsets, attributes, and other useful development information through the debug interface. Status and console messages provide visible feedback when profiles, backups, and ROM data change.

## Designed to Grow

1. **Human-Readable Profiles**

   Profiles use JSON, making their structure visible, portable, and approachable. Supporting a new hack can begin with a new profile rather than a completely separate editor.

2. **Profile-Defined Capabilities**

   Profiles can describe offsets, backup regions, game-text layouts, behavior options, and supported editing features. Tools can therefore adapt to the active project instead of assuming that every ROM is organized identically.

3. **Modular Components**

   Profile management, ROM editing, backup operations, dialogs, text tables, and application behavior are separated into focused modules. This provides clear places for new capabilities to take root.

4. **Expandable Text Support**

   Text tables allow additional character encodings and project-specific alphabets to be introduced without redesigning the entire application.

5. **Feature-Based Evolution**

   New editing tools can be exposed only by profiles that support them. Experimental or hack-specific capabilities can be added without forcing every project into the same workflow.

6. **Welcoming Contributions**

   There are many meaningful ways to help Blue Wing grow:

   1. Add or improve project profiles
   2. Introduce new text tables
   3. Build new editing views
   4. Improve ROM validation and error reporting
   5. Expand backup and restoration tools
   6. Refine documentation and usability
   7. Share ideas discovered through real ROM-hacking work

## The Road Ahead

Blue Wing is meant to become more than a collection of fixed editing commands. Its goal is to provide a dependable foundation on which new SMB3 tools, project formats, and creative workflows can be built.

Every new profile expands the range of projects Blue Wing can understand. Every new editor opens another part of the ROM to experimentation. Every contribution can make ambitious SMB3 hacking more approachable for the next creator.

The wings are open. Let’s see how far this can fly.

## ROM Notice

Blue Wing does not include commercial ROM files. Users are responsible for supplying legally obtained ROMs and for following the laws that apply in their location.
