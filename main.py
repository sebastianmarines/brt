import random
from mesa import Agent, Model
from mesa.time import RandomActivation

from pydantic import BaseModel
from fastapi import FastAPI

app = FastAPI()

import random
from mesa import Agent, Model
from mesa.time import RandomActivation

from pydantic import BaseModel


class Estacion(BaseModel):
    nombre: str
    posicion: tuple[int, int]
    pasajeros: int


class ResultadoEstacion(BaseModel):
    estacion: str
    pasajeros_suben: int
    pasajeros_bajan: int
    cargando: bool = False


class Data(BaseModel):
    estaciones: list[Estacion]
    ruta_brt: list[int]
    resultados_por_estacion: list[ResultadoEstacion]


class BusStation(Agent):
    def __init__(self, unique_id, name, model, x_coordinate, has_charging_station=False):
        super().__init__(unique_id, model)
        self.name = name
        self.people_waiting = random.randint(0, 20)  # Random number of people at the station
        self.x_coordinate = x_coordinate
        self.has_charging_station = has_charging_station

    def __str__(self):
        return f"BusStation-{self.name}"

    def step(self):
        # Stations might have additional behaviors or events in a more complex simulation
        pass


class Bus(Model):
    def __init__(self, stations_info, max_capacity, battery_capacity):
        super().__init__()
        self.max_capacity = max_capacity
        self.battery_capacity = battery_capacity
        self.battery = battery_capacity  # Current charge of the bus battery
        self.passengers = 0
        self.current_station_index = 0
        self.schedule = RandomActivation(self)
        self.data = Data(estaciones=[], ruta_brt=[], resultados_por_estacion=[])

        # Define stations including their coordinates and whether they have a charging station
        self.stations = [
            BusStation(i, name, self, x_coordinate, has_charging_station)
            for i, (name, x_coordinate, has_charging_station) in enumerate(stations_info)
        ]

        self.data.estaciones = [
            Estacion(nombre=station.name, posicion=(station.x_coordinate, 0), pasajeros=station.people_waiting)
            for station in self.stations
        ]

        self.data.ruta_brt = [station.x_coordinate for station in self.stations]

        for station in self.stations:
            self.schedule.add(station)

        self.charging_rate = 60  # Amount of battery the bus charges per step at the charging station

    def discharge_battery(self, distance):
        # Discharge rate can be defined as per unit of distance
        discharge_rate = 0.1  # Assuming 1 unit of battery for 1 unit of distance
        self.battery -= distance * discharge_rate

    def step(self):
        current_station = self.stations[self.current_station_index]

        # Simulate people getting off the bus randomly
        people_exiting = min(self.passengers, random.randint(0, 5))
        self.passengers -= people_exiting

        # Simulate people getting on the bus, ensuring we don't exceed capacity
        people_entering = min(current_station.people_waiting, self.max_capacity - self.passengers)
        current_station.people_waiting -= people_entering
        self.passengers += people_entering

        # Check whether the bus should charge its battery at this station
        if current_station.has_charging_station:
            charge = self.battery + self.charging_rate
            self.battery = charge if charge <= self.battery_capacity else self.battery_capacity
            # print(f"Charging at {current_station}, new battery: {self.battery}")
            charging_status = " (Charging)"
        else:
            charging_status = ""

        # Discharge the battery based on the distance to the next station
        next_station_index = (self.current_station_index + 1) % len(self.stations)
        next_station = self.stations[next_station_index]
        distance_to_next_station = abs(next_station.x_coordinate - current_station.x_coordinate)

        # Print the current state
        print(f"Step {self.schedule.steps}:")
        print(
            f"  Bus at {current_station}{charging_status}-({current_station.x_coordinate}), Passengers on bus: {self.passengers}, Battery: {self.battery}/{self.battery_capacity}")
        for station in self.stations:
            print(f"  {station}: People waiting: {station.people_waiting}")

        self.data.resultados_por_estacion.append(
            ResultadoEstacion(
                estacion=current_station.name,
                pasajeros_suben=people_entering,
                pasajeros_bajan=people_exiting,
                cargando=current_station.has_charging_station
            )
        )

        # Move to the next station
        self.discharge_battery(distance_to_next_station)
        self.current_station_index = next_station_index


@app.get("/")
def read_root() -> Data:
    stations_info = [
        ("Estanzuela", 0, False),
        ("Centro", 5, False),
        ("Tec", 10, False),
        ("San Pedro", 20, True),
        ("Santa Catarina", 40, False),
    ]

    model = Bus(stations_info, max_capacity=30, battery_capacity=100)
    for _ in stations_info:  # Number of steps to simulate
        model.step()

    return model.data


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)