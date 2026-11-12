from lib.workout_set import WorkoutSet


class WorkoutSetRepository:

    def __init__(self, connection):
        self._connection = connection

    def create(self, set_data, workout_id):
        exercise_id = set_data.get("exercise_id")
        reps = set_data.get("reps")
        if not exercise_id or not reps:
            return False
        next_set_number = self._next_set_number(workout_id, exercise_id)
        new_set = WorkoutSet(
            workout_id=workout_id,
            exercise_id=exercise_id,
            set_number=next_set_number,
            reps=reps,
            weight=set_data.get("weight") or None
        )
        result = self._connection.execute(
            "INSERT INTO workout_sets "
            "(workout_id, exercise_id, set_number, reps, weight) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            [new_set.workout_id, new_set.exercise_id,
                new_set.set_number, new_set.reps, new_set.weight]
        )
        new_set.id = result[0]["id"]
        return new_set

    def find_by_id(self, workout_set_id):
        try:
            workout_set = self._connection.execute(
                "SELECT * FROM workout_sets WHERE id = %s", [workout_set_id]
            )[0]
        except IndexError:
            return None

        return WorkoutSet(**workout_set)

    def find_by_workout_id(self, workout_id):
        rows = self._connection.execute(
            "SELECT * FROM workout_sets WHERE workout_id = %s ORDER BY exercise_id, set_number", 
            [workout_id]
        )
        return [WorkoutSet(**row) for row in rows]

    def update(self, set_id, set_data):
        reps = set_data.get("reps")
        weight = set_data.get("weight") or None
        self._connection.execute(
            "UPDATE workout_sets SET reps = %s, weight = %s WHERE id = %s",
            [reps, weight, set_id]
        )

    def delete(self, set_id):
        row = self._connection.execute(
            "SELECT workout_id, exercise_id, set_number " \
            "FROM workout_sets WHERE id = %s",
            [set_id]
        )
        if not row:
            return
        workout_id = row[0]["workout_id"]
        exercise_id = row[0]["exercise_id"]
        set_number = row[0]["set_number"]
        self._connection.execute(
            "DELETE FROM workout_sets WHERE id = %s",
            [set_id]
        )
        self._connection.execute(
            "UPDATE workout_sets " \
            "SET set_number = set_number - 1 " \
            "WHERE workout_id = %s AND exercise_id = %s AND set_number > %s",
            [workout_id, exercise_id, set_number]
        )


    def _next_set_number(self, workout_id, exercise_id):
        rows = self._connection.execute(
            "SELECT COUNT(*) AS count FROM workout_sets WHERE workout_id = %s AND exercise_id = %s",
            [workout_id, exercise_id]
        )
        return rows[0]["count"] + 1
