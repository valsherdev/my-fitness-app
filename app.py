import os
from flask import Flask, request, render_template, redirect, session, flash
from lib.database_connection import (
    get_flask_database_connection, DatabaseConnection)
from lib.user_repository import UserRepository
from lib.workout_repository import WorkoutRepository
from lib.exercise_repository import ExerciseRepository
from lib.workout_set_repository import WorkoutSetRepository
from dotenv import load_dotenv
from login_required import login_required_decorator
from flask_bcrypt import Bcrypt


load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]


@app.route("/dashboard", methods=["GET"])
@login_required_decorator
def dashboard():
    connection = get_flask_database_connection(app)
    user_repo = UserRepository(connection)
    user = user_repo.find_by_id(session["user_id"])
    workout_repo = WorkoutRepository(connection)
    in_progress = workout_repo.find_in_progress(session["user_id"])
    recent_workouts = workout_repo.show_summaries(session["user_id"], limit=3)
    return render_template("dashboard.html", user=user,
                           in_progress=in_progress,
                           recent_workouts=recent_workouts)


@app.route("/workouts/start", methods=["POST"])
@login_required_decorator
def start_workout():
    connection = get_flask_database_connection(app)
    workout_repo = WorkoutRepository(connection)
    if workout_repo.find_in_progress(session["user_id"]) is not None:
        flash("You already have a workout in progress.")
        return redirect("/dashboard")
    new_workout = workout_repo.start(user_id=session["user_id"])
    return redirect(f"/workouts/{new_workout.id}")


@app.route("/workouts/log", methods=["POST"])
@login_required_decorator
def log_past_workout():
    connection = get_flask_database_connection(app)
    workout_repo = WorkoutRepository(connection)
    workout_details = request.form
    new_workout = workout_repo.log_past(
        workout_details, user_id=session["user_id"])
    if new_workout is False:
        flash("Please fill in start and end times.")
        return redirect("/dashboard")
    return redirect(f"/workouts/{new_workout.id}")


@app.route("/workouts/<workout_id>", methods=["GET"])
@login_required_decorator
def get_individual_workout(workout_id):
    connection = get_flask_database_connection(app)
    workout_repo = WorkoutRepository(connection)
    exercise_repo = ExerciseRepository(connection)
    set_repo = WorkoutSetRepository(connection)
    workout = workout_repo.find_by_id(workout_id)
    if workout is None or workout.user_id != session["user_id"]:
        return render_template("workout_view_fail.html")
    muscle_groups = exercise_repo.muscle_groups()
    selected_group = request.args.get("muscle_group")
    if selected_group:
        exercises_for_dropdown = exercise_repo.find_by_muscle_group(selected_group)
    else:
        exercises_for_dropdown = []
    all_exercises = exercise_repo.all()
    all_sets = set_repo.find_by_workout_id(workout_id)
    sets_by_exercise = {}
    for workout_set in all_sets:
        sets_by_exercise.setdefault(workout_set.exercise_id, []).append(workout_set)    
    return render_template(
        "workout_page.html", 
        workout=workout,
        muscle_groups=muscle_groups,
        selected_group=selected_group,
        exercises_for_dropdown=exercises_for_dropdown, 
        all_exercises=all_exercises, 
        sets_by_exercise=sets_by_exercise
        )

@app.route("/workouts/<workout_id>/delete", methods=["POST"])
@login_required_decorator
def delete_workout(workout_id):
    connection = get_flask_database_connection(app)
    workout_repo = WorkoutRepository(connection)
    workout = workout_repo.find_by_id(workout_id)
    if workout is None or workout.user_id != session["user_id"]:
        return render_template("workout_view_fail.html")
    workout_repo.delete(workout_id)
    flash("Workout deleted successfully.")
    return redirect("/workouts")


@app.route("/workouts/<workout_id>/sets", methods=["POST"])
@login_required_decorator
def add_set(workout_id):
    connection = get_flask_database_connection(app)
    set_repo = WorkoutSetRepository(connection)
    workout_repo = WorkoutRepository(connection)
    workout = workout_repo.find_by_id(workout_id)
    if workout is None or workout.user_id != session["user_id"]:
        return render_template("workout_view_fail.html")
    if workout.ended_at is not None:
        flash("This workout has already been completed. You cannot add more sets.")
        return redirect(f"/workouts/{workout_id}")
    set_data = request.form
    new_set = set_repo.create(set_data, workout_id)
    if new_set is False:
        flash("Please choose an exercise and enter reps.")
    return redirect(f"/workouts/{workout_id}")

@app.route("/workouts/<workout_id>/sets/<set_id>/edit", methods=["POST"])
@login_required_decorator
def edit_set(workout_id, set_id):
    connection = get_flask_database_connection(app)
    set_repo = WorkoutSetRepository(connection)
    workout_repo = WorkoutRepository(connection)
    workout = workout_repo.find_by_id(workout_id)
    workout_set = set_repo.find_by_id(set_id)
    if workout is None or workout.user_id != session["user_id"]:
        return render_template("workout_view_fail.html")
    if workout_set is None or workout_set.workout_id != int(workout_id):
        return render_template("workout_view_fail.html")
    set_data = request.form
    set_repo.update(set_id, set_data)
    flash("Set updated successfully.")
    return redirect(f"/workouts/{workout_id}")

@app.route("/workouts/<workout_id>/sets/<set_id>/delete", methods=["POST"])
@login_required_decorator
def delete_set(workout_id, set_id):
    connection = get_flask_database_connection(app)
    set_repo = WorkoutSetRepository(connection)
    workout_repo = WorkoutRepository(connection)
    workout = workout_repo.find_by_id(workout_id)
    workout_set = set_repo.find_by_id(set_id)
    if workout is None or workout.user_id != session["user_id"]:
        return render_template("workout_view_fail.html")
    if workout_set is None or workout_set.workout_id != int(workout_id):
        return render_template("workout_view_fail.html")
    set_repo.delete(set_id)
    flash("Set deleted successfully.")
    return redirect(f"/workouts/{workout_id}")

@app.route("/workouts/<workout_id>/finish", methods=["POST"])
@login_required_decorator
def finish_workout(workout_id):
    connection = get_flask_database_connection(app)
    workout_repo = WorkoutRepository(connection)
    workout_repo.finish(workout_id)
    return redirect("/dashboard")

@app.route("/workouts", methods=["GET"])
@login_required_decorator
def workout_history():
    connection = get_flask_database_connection(app)
    workout_repo = WorkoutRepository(connection)
    workout_history = workout_repo.show_summaries(session["user_id"])
    return render_template(
        "workout_history.html", 
        workout_history=workout_history
    )


# --- SIGNUP PAGE ---
@app.route("/", methods=["GET"])
def signup():
    if session.get("user_id"):
        return redirect("/dashboard")
    return render_template("signup_form.html")


@app.route("/", methods=["POST"])
def create_user():
    signup_form_data = request.form
    connection = get_flask_database_connection(app)
    user_repo = UserRepository(connection)
    new_user = user_repo.create(signup_form_data)
    if new_user is False:
        return redirect("/sign-up/failed")
    session["user_id"] = new_user.id
    return redirect("/dashboard")


# --- LOGIN PAGE ---
@app.route("/sessions/new", methods=["GET"])
def get_login_form():
    return render_template("login_form.html")


@app.route("/sessions", methods=["POST"])
def create_session():
    login_form_data = request.form
    connection = get_flask_database_connection(app)
    user_repo = UserRepository(connection)
    user = user_repo.find_by_email(login_form_data["email"])
    if user is None:
        return redirect("/sessions/failed")
    if user_repo.check_password(user, login_form_data["password"]):
        session["user_id"] = user.id
        return redirect("/dashboard")
    else:
        return redirect("/sessions/failed")


# --- FAIL PAGES ---
@app.route("/sessions/failed", methods=["GET"])
def login_form_fail():
    return render_template("login_failed.html")


@app.route("/sign-up/failed", methods=["GET"])
def signup_form_fail():
    return render_template("signup_failed.html")


# --- LOGOUT ---
@app.route("/logout", methods=["GET"])
@login_required_decorator
def logout():
    session["user_id"] = None
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5001)))
