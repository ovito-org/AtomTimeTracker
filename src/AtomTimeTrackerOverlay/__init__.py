#### Atom Time Tracker ####
# Track grains,clusters, etc. over time

import networkx as nx
from ovito.data import DataCollection
from ovito.vis import ViewportOverlayInterface
from traits.api import Float, Int, Map, Range


class AtomTimeTracker(ViewportOverlayInterface):
    group1 = "Plot Settings"
    hspace = Float(1.0, label="Horizontal node spacing", ovito_group=group1)
    vspace = Float(1.0, label="Vertical node spacing", ovito_group=group1)
    start_frame = Int(0, label="First frame", ovito_group=group1)
    end_frame = Int(-1, label="Last frame", ovito_group=group1)
    font_size = Float(12.0, label="Font size", ovito_group=group1)

    group2 = "Positioning"
    alignment = Map(
        {
            "Top left": (0.0, 1.0, "north west"),
            "Top": (0.5, 1.0, "north"),
            "Top right": (1.0, 1.0, "north east"),
            "Right": (1.0, 0.5, "east"),
            "Bottom right": (1.0, 0.0, "south east"),
            "Bottom": (0.5, 0.0, "south"),
            "Bottom left": (0.0, 0.0, "south west"),
            "Left": (0.0, 0.5, "west"),
        },
        label="Alignment",
        ovito_group=group2,
    )
    px = Range(
        low=-1.0,
        high=1.0,
        value=0.0,
        label="X-offset",
        ovito_unit="percent",
        ovito_group=group2,
    )
    py = Range(
        low=-1.0,
        high=1.0,
        value=0.0,
        label="Y-offset",
        ovito_unit="percent",
        ovito_group=group2,
    )
    w = Range(
        low=0.05,
        high=1,
        value=0.5,
        label="Width",
        ovito_unit="percent",
        ovito_group=group2,
    )
    h = Range(
        low=0.05,
        high=1,
        value=0.5,
        label="Height",
        ovito_unit="percent",
        ovito_group=group2,
    )
    alpha = Range(
        low=0.0,
        high=1.0,
        value=1.0,
        label="Opacity",
        ovito_unit="percent",
        ovito_group=group2,
    )

    def render(
        self,
        canvas: ViewportOverlayInterface.Canvas,
        data: DataCollection,
        frame: int,
        **_,
    ):

        cache_key_base = "AtomTimeTracking"
        cache_key_data = cache_key_base + ".data"
        assert cache_key_data in data.attributes

        cache_key_params = cache_key_base + ".params"
        assert cache_key_params in data.attributes

        start_value, start_frame = data.attributes[cache_key_params]

        if start_frame == -1 or start_value < 1:
            return
        sub_graph = nx.dfs_tree(
            data.attributes[cache_key_data], (start_frame, start_value)
        )

        layout = {}
        labels = {}
        colors = []
        sub_graph_draw = sub_graph.copy()
        for node in sub_graph:
            if node[0] < self.start_frame:
                continue
            if self.end_frame != -1 and node[0] >= self.end_frame:
                sub_graph_draw.remove_node(node)
                continue
            layout[node] = (node[0] * self.hspace, node[1] * self.vspace)
            labels[node] = f"{node[0]}, {node[1]}"
            if node[0] == frame:
                colors.append("tab:blue")
            elif node[0] == start_frame:
                colors.append("tab:orange")
            else:
                colors.append("none")

        with canvas.mpl_figure(
            pos=(self.alignment_[0] + self.px, self.alignment_[1] + self.py),
            size=(self.w, self.h),
            anchor=self.alignment_[2],
            alpha=self.alpha,
            tight_layout=True,
        ):
            nx.draw(
                sub_graph_draw,
                pos=layout,
                node_color=colors,
                node_shape="s",
                labels=labels,
                node_size=1000,
                font_size=self.font_size,
            )
