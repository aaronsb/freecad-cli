"""Part primitives.

The generated verbs are alphabetical and every property is optional, so
`cylinder` prompts for Angle before Height and lets you skip Radius. These
say what a Part primitive actually asks for, in the order a person expects.
"""

PATCH = {
    "key": "Part",
    "types": {
        "Part::Box": {
            "verb": "box", "aliases": ["bx"],
            "doc": "Create a box from three dimensions.",
            "steps": ["Length", "Width", "Height"],
            "prompts": {"Length": "Length", "Width": "Width",
                        "Height": "Height"},
            "strict": True,
        },
        "Part::Cylinder": {
            "verb": "cylinder", "aliases": ["cyl"],
            "doc": "Create a cylinder from a radius and a height.",
            "steps": ["Radius", "Height"],
            "options": ["Angle"],
            "hide": ["FirstAngle", "SecondAngle"],
            "strict": True,
        },
        "Part::Sphere": {
            "verb": "sphere", "aliases": ["sph"],
            "doc": "Create a sphere from a radius.",
            "steps": ["Radius"],
            "options": ["Angle1", "Angle2", "Angle3"],
            "strict": True,
        },
        "Part::Cone": {
            "verb": "cone",
            "doc": "Create a cone from two radii and a height.",
            "steps": ["Radius1", "Radius2", "Height"],
            "options": ["Angle"],
            "strict": True,
        },
        "Part::Torus": {
            "verb": "torus",
            "doc": "Create a torus from two radii.",
            "steps": ["Radius1", "Radius2"],
            "options": ["Angle1", "Angle2", "Angle3"],
            "strict": True,
        },
        "Part::Wedge": {
            "verb": "wedge",
            "steps": ["Xmin", "Ymin", "Zmin", "Xmax", "Ymax", "Zmax"],
            "strict": True,
        },
        "Part::Helix": {
            "verb": "helix",
            "doc": "Create a helix from a pitch, a height and a radius.",
            "steps": ["Pitch", "Height", "Radius"],
            "options": ["Angle", "LocalCoord", "Style"],
            "strict": True,
        },
        # These collide with the hand-written Draft verbs, which pick points
        # in the viewport. The generated versions would shadow them.
        "Part::Line": {"skip": True},
        "Part::Vertex": {"skip": True},
    },
}
