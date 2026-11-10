from lib.workout import Workout
from datetime import datetime, timezone


class WorkoutRepository:

    def __init__(self, connection):
        self._connection = connection

    def start(self, user_id):
        new_workout = Workout(
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            notes=None
        )
        result = self._connection.execute(
            "INSERT INTO workouts (user_id, started_at, ended_at, notes) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            [new_workout.user_id, new_workout.started_at,
                new_workout.ended_at, new_workout.notes]
        )
        new_workout.id = result[0]["id"]
        return new_workout

    def log_past(self, workout_data, user_id):
        new_workout = Workout(
            user_id=user_id,
            started_at=workout_data.get("started_at"),
            ended_at=workout_data.get("ended_at"),
            notes=workout_data.get("notes")
        )

        if not new_workout.started_at or not new_workout.ended_at:
            return False
        if new_workout.ended_at < new_workout.started_at:
            return False

        result = self._connection.execute(
            "INSERT INTO workouts (user_id, started_at, ended_at, notes) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            [
                new_workout.user_id,
                new_workout.started_at,
                new_workout.ended_at,
                new_workout.notes
            ]
        )
        new_workout.id = result[0]["id"]
        return new_workout

    def find_by_id(self, workout_id):
        try:
            workout = self._connection.execute(
                "SELECT * FROM workouts WHERE id = %s", [workout_id]
            )[0]
        except IndexError:
            return None

        return Workout(**workout)

    def find_by_user_id(self, user_id):
        rows = self._connection.execute(
                "SELECT * FROM workouts WHERE user_id = %s", [user_id]
        )
      
        if not rows:
            return None
        return [Workout(**row) for row in rows]

    def find_in_progress(self, user_id):
        rows = self._connection.execute(
            "SELECT * FROM workouts WHERE user_id = %s AND ended_at IS NULL", [
                user_id]
        )
        if not rows:
            return None
        return Workout(**rows[0])

    def finish(self, workout_id):
        self._connection.execute(
            "UPDATE workouts SET ended_at = %s WHERE id = %s",
            [datetime.now(timezone.utc), workout_id]
        )


    def show_summaries(self, user_id, limit=None):
        query = """
            SELECT 
                w.id, 
                w.started_at, 
                w.ended_at,
                COUNT(ws.id) AS total_sets,
                COUNT(DISTINCT ws.exercise_id) AS exercise_count 
            FROM workouts w 
            LEFT JOIN workout_sets ws ON ws.workout_id = w.id 
            WHERE w.user_id = %s 
            AND w.ended_at IS NOT NULL
            GROUP BY w.id 
            ORDER BY w.started_at DESC
        """
        params = [user_id]
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        rows = self._connection.execute(query, params)
        return [dict(row) for row in rows]
        
