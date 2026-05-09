import random
import math


class PSOFacilityOptimizer:

    def __init__(
        self,
        graph,
        num_facilities=10,
        num_particles=20,
        iterations=30
    ):

        self.graph = graph
        self.nodes = list(graph.nodes())

        self.num_facilities = num_facilities
        self.num_particles = num_particles
        self.iterations = iterations

    # ---------------------------------------------------
    # FITNESS
    # ---------------------------------------------------

    def fitness(self, facilities):

        total_distance = 0

        sample_nodes = random.sample(
            self.nodes,
            min(500, len(self.nodes))
        )

        for node in sample_nodes:

            node_x = self.graph.nodes[node]["x"]
            node_y = self.graph.nodes[node]["y"]

            best = float("inf")

            for facility in facilities:

                fx = self.graph.nodes[facility]["x"]
                fy = self.graph.nodes[facility]["y"]

                dist = math.sqrt(
                    (node_x - fx) ** 2 +
                    (node_y - fy) ** 2
                )

                best = min(best, dist)

            total_distance += best

        return total_distance

    # ---------------------------------------------------
    # OPTIMIZE
    # ---------------------------------------------------

    def optimize(self):

        particles = []

        for _ in range(self.num_particles):

            facilities = random.sample(
                self.nodes,
                self.num_facilities
            )

            particles.append({
                "position": facilities,
                "best_position": facilities[:],
                "best_score": self.fitness(facilities)
            })

        global_best = None
        global_best_score = float("inf")

        for _ in range(self.iterations):

            for particle in particles:

                score = self.fitness(
                    particle["position"]
                )

                if score < particle["best_score"]:

                    particle["best_score"] = score

                    particle["best_position"] = (
                        particle["position"][:]
                    )

                if score < global_best_score:

                    global_best_score = score

                    global_best = (
                        particle["position"][:]
                    )

                # Random mutation

                new_position = (
                    particle["position"][:]
                )

                idx = random.randint(
                    0,
                    self.num_facilities - 1
                )

                new_position[idx] = random.choice(
                    self.nodes
                )

                particle["position"] = new_position

        return global_best