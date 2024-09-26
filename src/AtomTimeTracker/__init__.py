#### Atom Time Tracker ####
# Track grains,clusters, etc. over time

from collections import deque

import networkx as nx
import numpy as np
from ovito.data import DataCollection, DataObject, Particles
from ovito.pipeline import ModifierInterface
from ovito.traits import PropertyReference
from traits.api import Float, Int


class AtomTimeTracker(ModifierInterface):

    threshold = Float(0, label="Match threshold", ovito_group="Tracker")
    input_property = PropertyReference(
        container=DataObject.Ref(Particles),
        mode=PropertyReference.Mode.Properties,
        label="Input property",
        ovito_group="Tracker",
    )

    PropertyReference(
        container=DataObject.Ref(Particles),
        mode=PropertyReference.Mode.Properties,
        label="Property",
    )

    start_frame = Int(
        -1, label="Starting frame", ovito_invalidate_cache=False, ovito_group="Picker"
    )
    start_value = Int(
        -1, label="Starting value", ovito_invalidate_cache=False, ovito_group="Picker"
    )

    @staticmethod
    def get_sets(
        inp_prop: np.ndarray, particle_ids: np.ndarray
    ) -> dict[np.integer, set[np.integer]]:
        uni = np.unique(inp_prop)
        sets = {}
        for u in uni:
            loc = np.where(inp_prop == u)[0]
            sets[u] = set(particle_ids[loc])
        return sets

    def tracker(
        self,
        data: DataCollection,
        frame: int,
        input_slots: dict[str, ModifierInterface.InputSlot],
        data_cache: DataCollection,
    ):
        cache_key_base = "AtomTimeTracking"
        cache_key = cache_key_base + ".data"
        if cache_key not in data_cache.attributes:
            sets = deque()
            data_cache.attributes[cache_key] = nx.Graph()

            for frame in range(input_slots["upstream"].num_frames):
                frame_data = input_slots["upstream"].compute(frame)

                inp_prop = frame_data.particles[self.input_property]
                if not np.issubdtype(inp_prop.dtype, np.integer):
                    raise TypeError("Selected property needs to be integer type")
                if "Particle Identifier" in data.particles:
                    particle_ids = data.particles["Particle Identifier"]
                else:
                    particle_ids = np.arange(data.particles.count)

                sets.append(self.get_sets(inp_prop, particle_ids))

                if len(sets) == 2:
                    for k1, v1 in sets[0].items():
                        best_overlap = 0
                        best_idx = -1
                        for k2, v2 in sets[1].items():
                            inter = v1.intersection(v2)
                            overlap = len(inter) / len(v1)
                            if overlap > best_overlap:
                                best_overlap = overlap
                                best_idx = k2
                        assert k2 != -1
                        if best_overlap >= self.threshold:
                            data_cache.attributes[cache_key].add_edge(
                                (frame - 1, k1), (frame, best_idx)
                            )
                    sets.popleft()
                yield frame / input_slots["upstream"].num_frames

        data.attributes[cache_key] = data_cache.attributes[cache_key]
        return cache_key_base

    def picker(self, data: DataCollection, frame: int, cache_key_base: str):
        cache_key_data = cache_key_base + ".data"
        data.attributes[cache_key_base + ".params"] = (
            self.start_value,
            self.start_frame,
        )

        assert cache_key_data in data.attributes

        if self.start_frame == -1:
            return
        try:
            sub_graph = nx.dfs_tree(
                data.attributes[cache_key_data], (self.start_frame, self.start_value)
            )
        except nx.exception.NetworkXError:
            raise RuntimeError(
                f"Starting frame: {self.start_frame} and starting value: {self.start_value} not found in the dataset"
            )

        inp_prop = data.particles[self.input_property]
        selection = np.zeros(data.particles.count, dtype=int)
        for n in sub_graph.nodes:
            if n[0] == frame:
                selection = np.logical_or(selection, inp_prop == n[1])

        data.particles_.create_property("Selection", data=selection)

    def modify(
        self,
        data: DataCollection,
        frame: int,
        input_slots: dict[str, ModifierInterface.InputSlot],
        data_cache: DataCollection,
        **_,
    ):
        cache_key = yield from self.tracker(data, frame, input_slots, data_cache)
        self.picker(data, frame, cache_key)
