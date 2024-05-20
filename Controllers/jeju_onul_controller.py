from Schemas.base import Assembly, Request, Skills, Vehicle, Work
import shapely.geometry as geometry


class JejuOnulController:
    vehicles: dict[str, Vehicle]
    assemblies: dict[str, Assembly]
    works: dict[str, Work]
    skills: Skills

    def __init__(self, data: Request):
        self.vehicles = {vehicle.id: vehicle for vehicle in data.vehicles}
        self.assemblies = {assembly.id: assembly for assembly in data.assemblies}
        self.works = {work.id: work for work in data.works}
        self.boundaries = {
            boundary.id: geometry(boundary) for boundary in data.boundaries
        }
        self.skills = Skills(vehicles=data.vehicles)
        # self.id_handler = IdHandler()

        pickup_loc_cnt = {}
        delivery_loc_cnt = {}

        for _, work in self.works.items():
            for group, boudary in self.boundaries.items():
                pickup_loc = geometry.Point(work.pickup.location)
                delivery_loc = geometry.Point(work.delivery.location)

                if boudary.contains(pickup_loc):
                    work.pickup.group_id = group

                if boudary.contains(delivery_loc):
                    work.delivery.group_id = group

                if work.pickup.group_id and work.delivery.group_id:
                    break
            pickup_loc_cnt[tuple(work.pickup.location)] += 1
            delivery_loc_cnt[tuple(work.delivery.location)] += 1

        pickup_locs = set([location for location, _ in pickup_loc_cnt.items()])
        delivery_locs = set([location for location, _ in delivery_loc_cnt.items()])
