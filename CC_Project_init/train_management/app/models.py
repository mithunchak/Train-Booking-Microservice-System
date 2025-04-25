# app/models.py

class Train:
    def __init__(self, train_id, train_name, source, destination, departure, arrival, duration):
        self.train_id = train_id
        self.train_name = train_name
        self.source = source
        self.destination = destination
        self.departure = departure
        self.arrival = arrival
        self.duration = duration

    def to_dict(self):
        return {
            "train_id": self.train_id,
            "train_name": self.train_name,
            "source": self.source,
            "destination": self.destination,
            "departure": self.departure,
            "arrival": self.arrival,
            "duration": self.duration
        }
