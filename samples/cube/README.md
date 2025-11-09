# Cube Asset with VariantSet Example

This is an example of a USD asset that uses a **VariantSet** to allow users to choose between different model variations.

## Structure

- `cube_asset.usda` - The main asset file with a variant set
- `model/cube.usda` - The default cube model (closed)
- `model/cube_open.usda` - The open cube variant

## VariantSet

The `cube_asset.usda` file defines a variant set called `modelVariant` with two variants:

- **"default"** - References the closed cube model (`model/cube.usda`)
- **"open"** - References the open cube model (`model/cube_open.usda`)

## Changing the Default Variant

To change which variant is displayed by default, edit the `variants` dictionary in `cube_asset.usda`:

```usda
def Xform "cube_asset" (
    variants = {
        string modelVariant = "default"  # Change this to "open" to show the open cube by default
    }
    prepend variantSets = "modelVariant"
)
```

Simply change `"default"` to `"open"` (or vice versa) to switch the default variant selection.

## Usage in DCCs

In applications like Maya, you can:
1. Load the `cube_asset.usda` file
2. Find the `modelVariant` attribute on the `/cube_asset` prim
3. Use the dropdown to switch between "default" and "open" variants

The variant selection can be changed non-destructively at any time without modifying the underlying asset files.

