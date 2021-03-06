"""
Database Utilities & Database API

Creates tables and establishes relationships in Google Cloud SQL Database, and provides endpoints for accessing,
inserting, and updating data from Google Cloud SQL Database

`Link How to set up Google Cloud SQL instance <https://cloud.google.com/sql/docs/mysql/quickstart>`_

`Link Google Cloud proxy instructions <https://cloud.google.com/sql/docs/mysql/connect-external-app>`_

Short proxy instructions:

- Enable Cloud SQL Admin API for the project.
- Create a new Google Cloud SQL Instance, then create a database.
- Copy the INSTANCE_CONNECTION_NAME from overview screen
- Install the proxy client (as per google doc instructions), make it executable
- Invoke proxy via one of the following:
    - ./cloud_sql_proxy -instances=<INSTANCE_CONNECTION_NAME>=tcp:<PORT> &
    - ./cloud_sql_proxy -instances=<INSTANCE_CONNECTION_NAME>=tcp:<LOCAL_IP>:<PORT> &
- And update the below/db code to use the right port number, database name, etc.
"""

import csv
import json
import warnings
from datetime import datetime
from json.decoder import JSONDecodeError
from flask import Flask, Blueprint, request, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, Integer, Float, ForeignKey, LargeBinary
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from flask_marshmallow import Marshmallow
from marshmallow import fields
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import sessionmaker
from customer_app.utils import get_random_alphaNumeric_string, hash_password, verify_password, compare_dates, calc_hours
from sqlalchemy.dialects.mysql import TINYINT, VARCHAR, TEXT
from environs import Env

env = Env()
env.read_env()

DB_NAME = env("DB_NAME")
DB_USER = env("DB_USER")
DB_PASS = env("DB_PASS")
PORT_NUMBER = env("PORT_NUMBER")
DB_IP = env("DB_IP")
DB_URI = "mysql+pymysql://{}:{}@{}:{}/{}".format(DB_USER, DB_PASS, DB_IP, PORT_NUMBER, DB_NAME)

api = Blueprint("api", __name__)

db = SQLAlchemy()
engine = db.create_engine(
    sa_url=DB_URI,
    engine_opts={"echo": True}
)
session = sessionmaker(engine)

ma = Marshmallow()


class User(db.Model):
    """User Table - contains basic customer information"""
    __tablename__ = "user"
    username = db.Column('username', VARCHAR(12), primary_key=True, nullable=False)
    email = db.Column('email', VARCHAR(45), nullable=False)
    f_name = db.Column('first_name', VARCHAR(45), nullable=False)
    l_name = db.Column('last_name', VARCHAR(45), nullable=False)
    password = db.Column('password', TEXT(75), nullable=False)
    face_id = db.Column('face_id', TINYINT(1))
    register_date = db.Column('register_date', DateTime(), nullable=False)


class Employee(db.Model):
    """Employee table - contains basic employee information"""
    __tablename__ = "employee"
    username = db.Column('username', VARCHAR(12), primary_key=True, nullable=False)
    email = db.Column('email', VARCHAR(45), nullable=False)
    f_name = db.Column('first_name', VARCHAR(45), nullable=False)
    l_name = db.Column('last_name', VARCHAR(45), nullable=False)
    password = db.Column('password', TEXT(75), nullable=False)
    type = db.Column('type', VARCHAR(45), nullable=False)
    mac_address = db.Column('mac_address', VARCHAR(80), nullable=True)


class Car(db.Model):
    """Car Table - contains basic car information"""
    __tablename__ = "car"
    car_id = db.Column('car_id', VARCHAR(6), primary_key=True, nullable=False)
    model_id = db.Column('model_id', Integer(), ForeignKey('car_model.model_id', onupdate="CASCADE"), nullable=False)
    model = db.relationship("CarModel")
    name = db.Column('name', VARCHAR(45), nullable=False)
    cph = db.Column('cph', Float())
    locked = db.Column('locked', TINYINT(1), nullable=False)
    lng = db.Column('lng', Float())
    lat = db.Column('lat', Float())


class CarModel(db.Model):
    """CarModel Table - contains basic model/make information"""
    __tablename__ = "car_model"
    model_id = db.Column('model_id', Integer(), primary_key=True, nullable=False, autoincrement=True)
    make = db.Column('make', VARCHAR(45), nullable=False)
    model = db.Column('model', VARCHAR(45), nullable=False)
    year = db.Column('year', Integer(), nullable=False)
    capacity = db.Column('capacity', Integer(), nullable=False)
    colour = db.Column('colour', VARCHAR(45), nullable=False)
    transmission = db.Column('transmission', VARCHAR(6))
    weight = db.Column('weight', Integer())
    length = db.Column('length', Float())
    load_index = db.Column('load_index', Integer())
    engine_capacity = db.Column('engine_capacity', Float())
    ground_clearance = db.Column('ground_clearance', Integer())


class Booking(db.Model):
    """Booking Table - contains booking information"""
    __tablename__ = "booking"
    booking_id = db.Column('booking_id', Integer(), primary_key=True, nullable=False, autoincrement=True)
    user_id = db.Column(
        'user_id', VARCHAR(45),
        ForeignKey('user.username', ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False
    )
    user = db.relationship('User')
    car_id = db.Column(
        'car_id', VARCHAR(6),
        ForeignKey('car.car_id', ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False
    )
    car = db.relationship('Car')
    start = db.Column('start', DateTime(), nullable=False)
    end = db.Column('end', DateTime(), nullable=False)
    cost = db.Column('cost', Float())
    completed = db.Column('completed', Integer(), nullable=False)
    event_id = db.Column('event_id', VARCHAR(45))
    booking_date = db.Column('booking_date', DateTime(), nullable=False)


class CarReport(db.Model):
    """CarReport table: used to track repairs on vehicles"""
    __tablename__ = "car_report"
    report_id = db.Column('report_id', Integer(), primary_key=True, nullable=False, autoincrement=True)
    car_id = db.Column(
        'car_id', VARCHAR(6),
        ForeignKey('car.car_id', ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False
    )
    car = db.relationship('Car')
    engineer_id = db.Column(
        'engineer_id', VARCHAR(12),
        ForeignKey('employee.username', ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True
    )
    engineer = db.relationship('Employee')
    details = db.Column('details', VARCHAR(280), nullable=True)
    report_date = db.Column('report_date', DateTime(), nullable=False)
    complete_date = db.Column('complete_date', DateTime(), nullable=True)
    resolved = db.Column('resolved', TINYINT(1), default=0)
    priority = db.Column('priority', VARCHAR(6), default='LOW')
    notified = db.Column('notified', TINYINT(1), default=0, nullable=False)


class Encoding(db.Model):
    """Encoding Table: contains image encoding information (NOTE: not used currently, as per discussion forum advice)"""
    __tablename__ = "encoding"
    enc_id = db.Column('image_id', Integer(), primary_key=True, nullable=False, autoincrement=True)
    user_id = db.Column(
        'user_id', VARCHAR(45),
        ForeignKey('user.username', ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False
    )
    user = db.relationship('User')
    data = db.Column('data', LargeBinary(length=(2 ** 32) - 1), nullable=False)
    name = db.Column('name', VARCHAR(45))
    type = db.Column('type', VARCHAR(45))
    size = db.Column('size', VARCHAR(45))
    details = db.Column('details', VARCHAR(45))


class UserSchema(ma.Schema):
    """Schema to expose :class:`api.User` record information"""

    # noinspection PyMissingOrEmptyDocstring
    class Meta:
        model = User
        fields = ("username", "email", "f_name", "l_name", "face_id", "register_date")


class EmployeeSchema(ma.Schema):
    """Schema to expose :class:`api.Employee` record information"""

    # noinspection PyMissingOrEmptyDocstring
    class Meta:
        model = Employee
        fields = ("username", "email", "f_name", "l_name", "type", "mac_address")


class CarModelSchema(ma.Schema):
    """Schema to expose :class:`api.CarModel` record information"""

    # noinspection PyMissingOrEmptyDocstring
    class Meta:
        model = CarModel
        fields = ("model_id", "make", "model", "year", "capacity", "colour", "transmission", "weight", "length",
                  "load_index", "engine_capacity", "ground_clearance")


class CarSchema(ma.Schema):
    """Schema to expose :class:`api.Car` record information, including nested/foreign key records"""

    # noinspection PyMissingOrEmptyDocstring
    class Meta:
        model = Car
        fields = ("car_id", "name", "model_id", "model", "locked", "cph", "lat", "lng")

    model = fields.Nested(CarModelSchema)


class BookingSchema(ma.Schema):
    """Schema to expose :class:`api.Booking` record information, including nested/foreign key records"""

    # noinspection PyMissingOrEmptyDocstring
    class Meta:
        model = Booking
        fields = ("booking_id", "user_id", "cost", "user", "car_id", "car",
                  "start", "end", "completed", "event_id", "booking_date")

    user = fields.Nested(UserSchema)
    car = fields.Nested(CarSchema)


class ReportSchema(ma.Schema):
    """Schema to expose :class:`api.CarReport` table, including nested/foreign key records"""

    # noinspection PyMissingOrEmptyDocstring
    class Meta:
        model = CarReport
        fields = ("report_id", "car_id", "car", "engineer_id", "engineer", "details", "report_date", "complete_date",
                  "resolved", "priority", "notified")

    car = fields.Nested(CarSchema)
    engineer = fields.Nested(EmployeeSchema)


# noinspection PyMissingOrEmptyDocstring
def create_app():
    app = Flask(__name__)
    db.init_app(app)
    return app


@api.route("/employees", methods=['GET'])
def get_employees():
    """Endpoint to return employees from database

    Args:
        type: filter by employee type

    Returns:
        :class:`flask.Response`: 200 if successful along with employees as a json object, or 500 if no employees found
    """
    if request.args.get("type") is not None:  # get all employees by selected type
        employees = Employee.query.filter_by(type=request.args.get("type"))
    else:  # get all employees
        employees = Employee.query.all()
    if employees is not None:
        return Response(
            EmployeeSchema(many=True).dumps(employees), status=200, mimetype="application/json"
        )
    return Response("No employees found", status=500)


@api.route("/employee", methods=['GET'])
def get_employee():
    """Endpoint to return an employee from the database

    Args:
        employee_id: username of employee to return

    Returns:
        :class:`flask.Response`: 200 if successful, along with employee data as a json object, 404 if user was not
        found, or 400 if request parameters were missing
    """
    employee_id = request.args.get("employee_id")
    if employee_id is not None:
        employee = Employee.query.get(employee_id)
        if employee is not None:  # check if employee id is valid (employee exists)
            return Response(EmployeeSchema().dumps(employee), status=200, mimetype="application/json")
        return Response("Employee {} not found".format(employee_id), status=404)
    return Response("user_id param not found", status=400)


@api.route("/employee", methods=['POST'])
def create_employee():
    """Endpoint to create a new employee

    Args:
        employee_data: data to be added (username, email, password, names, type)

    Returns:
        :class:`flask.Response`: 200 if successful, 404 if employee already exists (email associated with another
        employee), 400 if invalid json structure/object
    """
    employee_data = request.get_json()
    response = None
    try:
        if employee_data is None:  # Check if user_data is provided or not
            response = Response(status=400)
        else:
            data = json.loads(employee_data)
            employee = Employee.query.get(data['username'])  # Check if username is already used
            if employee is None and update_employee_attributes(Employee(), data, create=True):
                response = Response(status=200)
            else:
                response = Response("Invalid employee_id: already exists", status=404)
    except JSONDecodeError:
        response = Response("Unable to decode employee object", status=400)
    except ValueError:
        response = Response("Unable to access value", status=400)
    finally:
        return response


def update_employee_attributes(employee: Employee, data: [], create: bool) -> bool:
    """Helper method to update/create employee record

    Args:
        employee: employee to update
        data: data to add
        create: boolean value indicating if create or update operation

    Returns:
        boolean value indicating if success/errors
    """
    try:
        salt = get_random_alphaNumeric_string(10)  # Randomise salt
        employee.username = data['username']
        employee.email = data['email']
        employee.f_name = data['f_name']
        employee.l_name = data['l_name']
        employee.type = data['type']
        employee.mac_address = data['mac_address']
        employee.password = hash_password(data['password'], salt) + ':' + salt
        if create:
            db.session.add(employee)  # Add employee to database
        db.session.commit()
        return True
    except (IntegrityError, InvalidRequestError, ValueError) as e:
        print(e)
        return False


@api.route("/employee/authenticate", methods=['GET', 'POST'])
def employee_authentication():
    """Endpoint to authenticate an employee logging in to MP webapp using username and password

    Args:
        employee_id: email input from user attempting login
        password: password input from user attempting login

    Returns:
        :class:`flask.Response`: 200 if successful, along with employee data as a json object, 400 if username/password
        parameter missing, 404 if password or username were invalid
    """
    employee_id = request.args.get('employee_id')
    password = request.args.get('password')
    if employee_id is None:  # Check if employee_id is provided
        response = Response("No username parameter found", status=400)
    elif password is None:  # Check if password is provided
        response = Response("No password parameter found", status=400)
    else:
        employee = Employee.query.get(employee_id)  # Retrieve employee with employee_id from database
        if employee is not None:
            stored_password = employee.password.split(':')[0]  # Retrieve hashed password from password string
            salt = employee.password.split(':')[1]  # Retrieve salt from password string
            if verify_password(stored_password, password, salt):  # Verify provided password using hashed password
                data = json.loads(EmployeeSchema().dumps(employee))  # Return employee detail for session
                response = Response(
                    json.dumps(data), status=200, content_type="application/json"
                )
            else:
                response = Response(json.dumps({'error': 'PASSWORD'}), status=404, content_type="application/json")
        else:
            response = Response(json.dumps({'error': 'USER'}), status=404, content_type="application/json")
    return response


@api.route("/employee", methods=['PUT'])
def update_employee():
    """Endpoint to update an existing employee details

    Args:
        data: json data containing employee fields to be updated

    Returns:
        :class:`flask.Response`: 200 if successful, along with new employee data as a json object, or 400 if json was
        invalid or employee username already exists, or 404 if the username pre-update did not exist
    """
    if request.args.get("update"):
        try:
            data = json.loads(request.get_json())
            employee = Employee.query.get(data["existing_username"])
            if employee is not None:  # check if existing employee_id is valid (exists)
                if update_employee_attributes(employee, data, create=False):
                    return Response(
                        UserSchema().dumps(Employee.query.get(data["username"])),
                        status=200
                    )
                return Response("Employee id already in use", status=400)  # new employee id already in use
            return Response("Invalid employee id (does not exist)", status=404)
        except JSONDecodeError:
            return Response("Incorrect JSON format", status=400)
        except ValueError:
            return Response("Incorrect JSON format", status=400)


@api.route("/employee", methods=['DELETE'])
def remove_employee():
    """Endpoint to remove an employee from the database

    Args:
        employee_id: id of employee to remove

    Returns:
        :class:`flask.Response`: 200 if successful, or 404 if employee_id is invalid,or 400 if missing request parameter
    """
    employee_id = request.args.get('employee_id')
    if employee_id is not None:
        employee = Employee.query.get(employee_id)
        if employee is not None:  # check if employee id is valid (exists)
            db.session.delete(employee)
            db.session.commit()
            return Response(status=200)
        return Response("Invalid employee_id: not found in db", status=404)
    return Response("Missing request param", status=400)


@api.route("/reports", methods=['GET'])
def get_reports():
    """Endpoint to retrieve multiple reports, optionally based on assignment to an engineer, or for a vehicle

    Args:
        car_id: rego of car reports to return
        engineer_id: username of employee assigned to a repair/report
        resolved: value filtering if a repair has been completed value (0 = false, 1 = true)

    Returns:
        :class:`flask.Response`: 200 if successful, along with report data as a json object
    """
    car_id = request.args.get("car_id")
    resolved = request.args.get("resolved")
    engineer_id = request.args.get("engineer_id")
    if resolved is not None:
        try:
            res_val = int(resolved)  # if set, enable filtering by resolved value (0 is not complete, 1 is completed)
            if res_val not in (1, 0):
                raise ValueError
        except ValueError:
            return Response("Incorrect resolved param value (must be 1 or 0)", status=400)
    if engineer_id is not None:  # return reports assigned to an engineer
        if resolved:
            reports = CarReport.query.filter_by(resolved=resolved).join(
                Employee).filter(Employee.username == engineer_id)
        else:
            reports = CarReport.query.join(Employee).filter(Employee.username == engineer_id)
    elif car_id is not None:  # return all uncompleted reports for a vehicle
        if resolved:
            reports = CarReport.query.filter_by(resolved=resolved).join(Car).filter(Car.car_id == car_id)
        else:
            reports = CarReport.query.join(Car).filter(Car.car_id == car_id)
    else:  # return all reports
        if resolved:
            reports = CarReport.query.filter_by(resolved=resolved)
        else:
            reports = CarReport.query.all()
    data = json.loads(ReportSchema(many=True).dumps(reports))
    for report in data:
        report['report_date'] = report['report_date'].replace("T", " ")
        if report['complete_date'] is not None:
            report['complete_date'] = report['complete_date'].replace("T", " ")
        else:
            report['complete_date'] = 0
        if report['engineer_id'] is None:
            report['engineer_id'] = 0
            report['engineer'] = 0
    return Response(json.dumps(data), status=200, mimetype="application/json")


@api.route("/report", methods=['GET'])
def get_report():
    """Returns a specific user from the database: access via report_id (int)

    Args:
        report_id: id of user to fetch from db

    Returns:
        :class:`flask.Response`: 200 if successful, along with report data as a json object, 404 if report was not
        found, 400 if request parameters were missing
    """
    report_id = request.args.get("report_id")
    if report_id is not None:
        report = CarReport.query.get(report_id)
        if report is not None:  # If report is in database
            return Response(ReportSchema().dumps(report), status=200, mimetype="application/json")
        return Response("report {} not found".format(report), status=404)
    return Response("report_id param not found", status=400)


@api.route("/report", methods=["POST"])
def create_report():
    """Endpoint to create a new report: created when admin completes repair form for a vehicle

    Args:
        data: report data to be added (report_date, priority, car_id, details)

    Returns:
        :class:`flask.Response`: 200 if successful, or 400 if json data was invalid
    """
    try:
        data = json.loads(request.get_json())
        report = CarReport()
        try:
            report.priority = data["priority"].upper()
        except KeyError:  # enable optional key - set to default value if not present
            print("no priority in received data - applying default (LOW)")
        report.car_id = data["car_id"]
        report.report_date = data["report_date"]
        report.details = data["details"]
        db.session.add(report)
        db.session.commit()
        return Response(ReportSchema().dumps(report), status=200, mimetype="application/json")
    except (JSONDecodeError, ValueError, KeyError):
        return Response("Unable to decode report object", status=400)


@api.route("/report", methods=['DELETE'])
def remove_report():
    """Endpoint to remove a report

    Args:
        report_id: id of report to remove

    Returns:
        :class:`flask.Response`: 200 if successful, 404 if report_id invalid, or 400 if missing request parameter
    """
    report_id = request.args.get('report_id')
    if report_id is not None:
        report = CarReport.query.get(report_id)
        if report is not None:  # check if report_id is valid (report exists)
            data = ReportSchema().dumps(report)
            db.session.delete(report)
            db.session.commit()
            return Response(data, status=200, mimetype="application/json")
        return Response("Invalid report_id: not found in database", status=404)
    return Response("Missing request parameter", status=400)


@api.route("/report", methods=["PUT"])
def update_report():
    """Endpoint to mark a report/repair as completed

    Args:
        report_id: id of report to complete (a car may have multiple reports, so this is required)
        engineer_id: id of the engineer who carried out the repair
        complete_date: datetime value of date of completion

    Returns:
        :class:`flask.Response`: 200 if successful, along with updated report data as a json object, 404 if report was
        not found, 400 if request parameters were missing
    """
    report_id = request.args.get("report_id")
    engineer_id = request.args.get("engineer_id")
    complete_date = request.args.get("complete_date")
    if None in (report_id, engineer_id, complete_date):
        return Response("Missing request params", status=400)
    report = CarReport.query.get(report_id)
    if report is None:
        return Response("Invalid report id: not found in database", status=404)
    engineer = Employee.query.get(engineer_id)
    if engineer is None or engineer.type != "ENGINEER":
        return Response("Invalid engineer id", status=404)
    report.engineer_id = engineer_id
    report.complete_date = datetime.strptime(complete_date, "%Y-%m-%d %H:%M:%S")
    report.resolved = 1
    report.notified = 1
    db.session.commit()
    return Response(ReportSchema().dumps(CarReport.query.get(report_id)), status=200)


@api.route("/report_notification", methods=['PUT'])
def update_report_notification():
    """Updates a repair reports notification status

    Args:
        report_id: id of report to update
        notification: value to update (0 or 1)

    Returns:
        :class:`flask.Response`: 200 if successful, 404 if report was not found, 400 if request parameters were missing
    """
    notification = request.args.get("notification")
    report_id = request.args.get("report_id")
    if None not in (report_id, notification):
        report = CarReport.query.get(report_id)
        if report is not None:
            try:
                notif_val = int(notification)
                if notif_val not in (0, 1):  # notifed must be 0 or 1
                    raise ValueError
            except ValueError:
                return Response("Invalid notification value: must be 0 or 1", status=400)
            report.notified = notif_val
            db.session.commit()
            return Response("Updated report: notified = {}".format(notif_val), status=200)
        return Response("Invalid report_id: not found in database", status=404)
    return Response("Missing request parameters", status=400)


@api.route("/users", methods=['GET'])
def get_users():
    """Endpoint to return ALL users from database (used in testing)"""
    users = User.query.all()
    if users is not None:
        return Response(UserSchema(many=True).dumps(users), status=200, mimetype="application/json")
    return Response("No users found", status=500)


@api.route("/user", methods=['GET'])
def get_user():
    """Returns a specific user from the database: acces via user_id (email)

    Args:
        user_id: id of user to fetch from db

    Returns:
        :class:`flask.Response`: 200 if successful, along with user data as a json object, 404 if user was not
        found, 400 if request parameters were missing
    """
    user_id = request.args.get('user_id')
    if user_id is not None:  # Check if user_id is provided
        user = User.query.get(user_id)
        if user is not None:  # If user is in database
            return Response(UserSchema().dumps(user), status=200, mimetype="application/json")
        return Response("User {} not found".format(user_id), status=404)
    return Response("user_id param not found", status=400)


@api.route("/user", methods=['POST'])
def add_user():
    """Adds a user to the database

    Args:
        user_data: data to be added (name, email, password, username) in the form of a json object

    Returns:
        :class:`flask.Response`: 200 if successful, 404 if user already exists (email associated with another user), 400
        if invalid json structure/object
    """
    user_data = request.get_json()
    response = None
    try:
        if user_data is None:  # Check if user_data is provided or not
            response = Response(status=400)
        else:
            data = json.loads(user_data)
            user = User.query.get(data['username'])  # Check if username is already used
            if user is None and update_user_attributes(User(), data, create=True):
                response = Response(status=200)
            else:
                response = Response("Invalid user_id: already exists", status=404)
    except JSONDecodeError:
        response = Response("Unable to decode user object", status=400)
    except ValueError:
        response = Response("Unable to access value", status=400)
    finally:
        return response


def update_user_attributes(user: User, data: [], create: bool) -> bool:
    """Helper method to create/update user attributes

    Args:
        user: user to update
        data: data to add
        create: boolean indicating if create/update operation

    Returns:
        boolean value indicating success/errors
    """
    try:
        salt = get_random_alphaNumeric_string(10)  # Randomise salt
        user.username = data['username']
        user.email = data['email']
        user.f_name = data['f_name']
        user.l_name = data['l_name']
        user.password = hash_password(data['password'], salt) + ':' + salt
        if create:
            user.register_date = datetime.now()
            user.face_id = 0
            db.session.add(user)  # Add user to database
        db.session.commit()
        return True
    except (IntegrityError, InvalidRequestError, ValueError):
        return False


@api.route("/users/authenticate", methods=['GET', 'POST'])
def user_authentication():
    """Endpoint to authenticate a user logging in to MP webapp using email and password

    Args:
        user_id: email input from user attempting login
        password: password input from user attempting login

    Returns:
        :class:`flask.Response`: 200 if successful, along with user data as a json object, 400 if email/password
        parameter missing, 404 if password or user_id were invalid
    """
    user_id = request.args.get('user_id')
    password = request.args.get('password')
    if user_id is None:  # Check if user_id is provided
        response = Response("No username parameter found", status=400)
    elif password is None:  # Check if password is provided
        response = Response("No password parameter found", status=400)
    else:
        user = User.query.get(user_id)  # Retrieve user with user_id from database
        if user is not None:
            stored_password = user.password.split(':')[0]  # Retrieve hashed password from password string
            salt = user.password.split(':')[1]  # Retrieve salt from password string
            if verify_password(stored_password, password, salt):  # Verify provided password using hashed password
                # and salt
                data = json.loads(UserSchema().dumps(user))  # Return user detail for session (no password returned)
                response = Response(
                    json.dumps(data), status=200, content_type="application/json"
                )
            else:
                response = Response(json.dumps({'error': 'PASSWORD'}), status=404, content_type="application/json")
        else:
            response = Response(json.dumps({'error': 'USER'}), status=404, content_type="application/json")
    return response


@api.route("/user", methods=['DELETE'])
def remove_user():
    """Endpoint to remove a user from the database

    Args:
        user_id: id of user to remove

    Returns:
        :class:`flask.Response`: 200 if successful, 400 if missing request params, or 404 if user id invalid
    """
    user_id = request.args.get('user_id')
    if user_id is not None:
        user = User.query.get(user_id)
        if user is not None:  # check if user is valid (exists in database)
            db.session.delete(user)
            db.session.commit()
            return Response(status=200)
        return Response("Invalid user_id: not found in db", status=404)
    return Response("Missing request param", status=400)


@api.route("/user", methods=['PUT'])
def update_user():
    """Updates an existing user details: face_id when register on MP

    Args:
        user_id: username of user to fetch from database
        face_id: value to update (1 if registered, 0 if not)

    Returns:
        :class:`flask.Response`: 200 if successful, along with user data as json object, 400 if invalid encoding, or if
        missing parameters, 404 if user idv invalid
    """
    if request.args.get("update"):  # update request: update all user attributes
        try:
            data = json.loads(request.get_json())
            username = data["existing_username"]
            user = User.query.get(username)
            if user is not None and update_user_attributes(user, data, create=False):
                return Response(UserSchema().dumps(User.query.get(data["username"])), status=200)
            return Response("Invalid user_id: not found in database", status=404)
        except JSONDecodeError:
            return Response("Received json data in improper format", status=400)
        except ValueError:
            return Response("Received json data in improper format", status=400)
    else:
        user_id = request.args.get("user_id")
        face_id = request.args.get("face_id")
        if None not in (user_id, face_id):  # Check if user_id and face_id are provided
            user = User.query.get(user_id)  # Retrieve user with user_id
            if user is not None:
                try:
                    val = int(face_id)
                    if val not in (0, 1):  # Update face_id boolean (1 if face_id is registered, 0 if not)
                        raise ValueError
                    user.face_id = val
                    db.session.commit()
                    return Response(
                        UserSchema().dumps(User.query.get(user_id)),
                        status=200
                    )
                except ValueError:
                    return Response("Incorrect face_id param: {}".format(face_id), status=400)
            return Response("User {} not found".format(user_id), status=404)
        return Response("Missing request params", status=400)


@api.route("/cars", methods=['GET'])
def get_cars():
    """Endpoint to return all the car objects in the database

    Returns:
        :class:`flask.Response`: 200 if successful, along with all cars as a json object, 500 if no cars found in db
    """
    cars = Car.query.all()  # Get all cars in the Car table
    if cars is not None:
        return Response(CarSchema(many=True).dumps(cars), status=200, mimetype="application/json")
    return Response("No cars found", status=500)


@api.route("/car", methods=['GET'])
def get_car():
    """Endpoint to return a car from the database with a specific car_id

    Args:
        car_id: id of car to fetch

    Returns:
        :class:`flask.Response`: 200 if successful, along with Car data as json object, 400 if request parameters are
        missing, 404 if car_id was invalid (not in DB)
    """
    car_id = request.args.get('car_id')
    if car_id is not None:  # Check if car_id is provided
        car = Car.query.get(car_id)  # Retrieve car with car_id
        if car is not None:
            return Response(CarSchema().dumps(car), status=200, mimetype="application/json")  # If car with car_id is
            # in the database, return car object
        return Response("Car not found", status=404)
    return Response("car_id param was not found", status=400)


@api.route("/car", methods=['POST'])
def create_car():
    """Endpoint to create a new vehicle

    Args:
        car_data: JSON data representing the new vehicle

    Returns:
        :class:`flask.Response`: 200 if successful, 400 if request parameters are missing or unable to decode json,
        404 if car_id was invalid (already exists)
    """
    car_data = request.get_json()
    try:
        if car_data is None:  # Check if user_data is provided or not
            return Response(status=400)
        else:
            data = json.loads(car_data)
            car = Car.query.get(data['car_id'])  # Check if username is already used
            if car is None and update_car_attributes(Car(), data, create=True):
                return Response(status=200)
            else:
                return Response("Invalid car_id: already exists", status=404)
    except JSONDecodeError:
        return Response("Unable to decode car object", status=400)
    except ValueError:
        return Response("Unable to access value", status=400)


@api.route("/update_car", methods=['PUT'])
def update_car():
    """Endpoint to update car attributes, including CarModel

    Args:
        data: json data containing new attribute values

    Returns:
        :class:`flask.Response`: 200 if successful, along with updated Car data as json object, or 400 if json was
        invalid or if the car_id already exists
    """
    try:
        data = json.loads(request.get_json())
        car = Car.query.get(data['existing_car_id'])
        if car is not None:
            if update_car_attributes(car, data, create=False):  # update car attributes and check if rego already exists
                return Response(
                    UserSchema().dumps(Car.query.get(data['car_id'])),
                    status=200
                )
            return Response('Car rego already exists', status=400)
    except (JSONDecodeError, ValueError, KeyError):
        return Response("Incorrect JSON format", status=400)


def update_car_attributes(car: Car, data: [], create: bool) -> bool:
    """Helper method to update a car item attributes (update or create

    Args:
        car: car to update
        data: data to add
        create: boolean value indicating if creating new row or updating existing

    Returns:
        boolean value indicating if successful/errors occured
    """
    try:
        car.car_id = data["car_id"]
        car.cph = float(data["cph"])
        car.lat = float(data["lat"])
        car.lng = float(data["lng"])
        car.name = data['name']
        car.model_id = data["model_id"]
        if create:
            car.locked = 1
            db.session.add(car)
        db.session.commit()
        return True
    except (IntegrityError, InvalidRequestError, ValueError) as e:
        print(e)
        return False


@api.route("/engineer/unlock_car", methods=['PUT'])
def engineer_unlock():
    """Endpoint for an Engineer to unlock a vehicle (during maintenance)

    Args:
        car_id: id of car to update
        engineer_id: id of engineer who is repairing the vehicle

    Returns:
        :class:`flask.Response`: 200 if successful, or 400 if missing parameters, or 404 if report_id or engineer_id are
        invalid (engineer_id can be invalid if an employee does not exist or if they are not an engineer)
    """
    car_id = request.args.get('car_id')
    engineer_id = request.args.get('engineer_id')
    if None not in (car_id, engineer_id):
        car = Car.query.get(car_id)
        engineer = Employee.query.get(engineer_id)
        if None not in (car, engineer) and engineer.type == "ENGINEER":  # must be engineer to unlock for repair
            if car.locked == 1:
                msg = "unlocked"
                car.locked = 0
            else:
                msg = "locked"
                car.locked = 1
            db.session.commit()
            return Response("Car {}".format(msg), status=200)
        return Response("Invalid engineer or car id", status=404)
    return Response("Missing request parameters", status=400)


@api.route("/car", methods=['PUT'])
def unlock_car():
    """Endpoint to update a car called from MP after it receives login information from AP. First, bookings matching
    the user_id and car_id are retrieved, and if they are valid (i.e. have not been completed or are within their
    start/end dates) then the car is unlocked. If the car is to be locked, then the booking is also marked as
    completed. If no user_id or locked value are included, this function calls update_location(car_id)

    Args:
        car_id: id of car to unlock
        locked: locked value to update to (1= locked, 0= unlocked)
        user_id: id of user in db
        lat: lat to update the car with
        lng: lng to update the car with

    Returns:
        :class:`flask.Response`: 200 if successful, 400 if there are client errors (invalid json format, missing
        parameters), 404 if no valid results found: no bookings for car,or no valid bookings (valid start/end dates) for
        the car
    """
    car_id = request.args.get('car_id')
    if car_id is not None:  # Check if car_id is is provided
        locked = request.args.get('locked')
        user_id = request.args.get('user_id')
        if None in (user_id, locked):  # Check if user_id and locked (1 or 0) are provided
            return update_location(car_id)
        else:
            try:
                locked_val = int(locked)
            except ValueError as e:  # Locked value must be 0 or 1 exception
                return Response("Invalid locked format: expected 1 or 0.\n".format(str(e)), status=400)
            status = 1 if locked_val == 0 else 0  # current locked status should be opposite of new status
            # query returns uncompleted bookings for the user and car, where the car.locked = status
            bookings = Booking.query \
                .filter_by(completed=0).filter_by(car_id=car_id).filter_by(user_id=user_id) \
                .join(Car).filter(Car.car_id == car_id).filter_by(locked=status)
            if bookings.count() > 0:  # If any bookings were found
                valid_bookings = []
                for booking in bookings:
                    if booking.start <= datetime.now():  # Booking has started and booking has not ended
                        valid_bookings.append(booking)
                if len(valid_bookings) == 0:  # No bookings found for user/car
                    return Response("No valid bookings were found", status=404)
                elif len(valid_bookings) > 1:  # There can only be one valid booking for a user and car
                    return Response("Multiple bookings found: database error", status=500)
                else:  # Valid booking found, so details are updated
                    Car.query.get(car_id).locked = locked_val
                    db.session.commit()
                    message = "Successful: car is {}".format("locked" if locked_val == 1 else "unlocked")
                if locked_val == 1:  # If car is to be locked/returned
                    Booking.query.get(valid_bookings[0].booking_id).completed = 1
                    db.session.commit()
                    if valid_bookings[0].end < datetime.now():  # car was returned after due date: add overdue message
                        message += ", return of car was overdue"
                    else:
                        message += ", booking has been completed"
                return Response(message, status=200)
            else:
                return Response("No bookings found - invalid parameters", status=404)
    return Response("Missing required params: car_id", status=400)


def update_location(car_id):
    """Updates the cars location coordinates in the db

    Args:
        car_id: id of car in db
        lat: lat to update the car with (request param)
        lng: lng to update the car with (request param)

    Returns:
        :class:`flask.Response`: 200 if successful, 400 if lng/lat invalid format: outside ranges, not float values, 404
         if car_id is invalid: not found in database
    """
    lng = request.args.get('lng')
    lat = request.args.get('lat')
    if None not in (lng, lat):  # Check if longitude and latitude are provided
        car = Car.query.get(car_id)  # Retrieve car with car_id
        if car is not None:
            try:
                fl_lng = float(lng)
                fl_lat = float(lat)
                if fl_lng > 180 or fl_lng < -180:  # Check if longitude is valid bound
                    raise ValueError("lng {} outside valid bounds".format(fl_lng))
                if fl_lat > 90 or fl_lat < -90:  # Check if latitude is in valid bound
                    raise ValueError("lat {}  outside valid bounds".format(fl_lat))
                car.lat = fl_lat  # Update car latitude
                car.lng = fl_lng  # Update car longitude
                db.session.commit()
                return Response("Updated coords: {} lat{},lng{}".format(car_id, lat, lng), status=200)
            except ValueError as ve:
                return Response("Invalid lat/lng format: {}".format(str(ve)), status=400)
        return Response("Car not found, invalid id{}".format(car_id), status=404)
    else:
        return Response("Missing required params: lat, lng", status=400)


@api.route("/car", methods=['DELETE'])
def remove_car():
    """Endpoint to remove a car from the database

    Args:
        car_id: id of car to remove

    Returns:
        :class:`flask.Response`: 200 if successful, 400 if missing request parameters, 404 if car_id is invalid
    """
    car_id = request.args.get('car_id')
    if car_id is not None:
        car = Car.query.get(car_id)
        if car is not None:
            db.session.delete(car)
            db.session.commit()
            return Response(status=200)
        return Response("Invalid rego: not found in db", status=404)
    return Response("Missing request parameter", status=400)


@api.route("/cars/<start>/<end>", methods=['GET'])
def get_valid_cars(start, end):
    """Returns a list of cars that are able to be booked between desired dates

    Args:
        start: start datetime of booking
        end: end datetime of booking

    Returns:
        JSON: object containing valid options for booking
    """
    bookings = Booking.query.filter_by(completed=0)
    booked_cars = []
    for booking in bookings:
        start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
        end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")
        if compare_dates(d_start=start_dt, d_end=end_dt, b_start=booking.start, b_end=booking.end):  # overlap found
            booked_cars.append(booking.car_id)  # add to booked car list: omit from returned cars
    cars = Car.query.filter(Car.car_id.notin_(booked_cars))  # cars that are not booked between dates
    return Response(CarSchema(many=True).dumps(cars), status=200, mimetype="application/json")


@api.route("/car_models", methods=['GET'])
def get_car_models():
    """Returns all car model from the database

    Returns:
        :class:`flask.Response`: 200 along with car models as JSON data
    """
    car_models = CarModel.query.all()
    return Response(CarModelSchema(many=True).dumps(car_models), status=200)


@api.route("/car_model", methods=['GET'])
def get_car_model():
    """Returns a Car Model from the database

    Args:
        model_id: id of model to fetch

    Returns:
        :class:`flask.Response`: 200 along with car model as JSON data, or 404 if model_id is invalid, or 400 if missing
        request parameter
    """
    model_id = request.args.get('model_id')
    if model_id is not None:
        model = CarModel.query.get(model_id)
        if model is not None:
            return Response(CarModelSchema().dumps(model), status=200, mimetype="application/json")
        return Response("Car model invalid: not found in database", status=404)
    return Response("Missing request parameter", status=400)


@api.route("/car_model", methods=['PUT'])
def update_car_model():
    """Endpoint to update an existing Vehicle model

    Args:
        car_data: JSON data representing the new vehicle

    Returns:
        :class:`flask.Response`: 200 if successful, 404 if invalid model_id, or 400 if missing request parameter or
        invalid JSON
    """
    model_data = request.get_json()
    try:
        if model_data is None:  # check if data is provided or not
            return Response("Missing json post data", status=400)
        else:
            data = json.loads(model_data)
            model = CarModel.query.get(data['model_id'])
            if model is not None and update_model(model, data, create=False):
                return Response(status=200)
            else:
                return Response("Invalid model_id: does not exist", status=404)
    except JSONDecodeError:
        return Response("Unable to decode model object", status=400)
    except ValueError:
        return Response("Unable to access value", status=400)


@api.route("/car_model", methods=['POST'])
def create_car_model():
    """Endpoint to create a new Vehicle model

    Args:
        car_data: JSON data representing the new vehicle

    Returns:
        :class:`flask.Response`: 200 if successful, or 400 if missing request parameter or invalid JSON
    """
    model_data = request.get_json()
    try:
        if model_data is None:  # Check if data is provided or not
            return Response("Missing json post data", status=400)
        else:
            data = json.loads(model_data)
            if update_model(CarModel(), data, create=True):
                return Response(status=200)
            return Response("error in accessing json data", status=400)
    except JSONDecodeError:
        return Response("Unable to decode model object", status=400)


def update_model(model: CarModel, data: [], create: bool) -> bool:
    """Helper method to update/add fields to a CarModel item

    Args:
        model: CarModel object, row to be updated
        data: list of data to add to model
        create: boolean indicating if update or create function

    Returns:
        bool value indicating success/error
    """
    try:
        model.make = data['make']
        model.model = data['model']
        model.year = data['year']
        model.capacity = data['capacity']
        model.colour = data['colour']
        model.transmission = data['transmission']
        model.weight = data['weight']
        model.length = data['length']
        model.load_index = data['load_index']
        model.engine_capacity = data['engine_capacity']
        model.ground_clearance = data['ground_clearance']
        if create:
            db.session.add(model)  # Add model to database
        db.session.commit()
        return True
    except JSONDecodeError:
        return False
    except ValueError:
        return False


@api.route("/bookings", methods=['GET'])
def get_bookings():
    """Returns a list of bookings, optionally with user_id returns bookings for a user

    Args:
        user_id: username of user to get bookings for
        status: filter bookings by their status (0 - booked, 1 - completed, 2 - cancelled)

    Returns:
        :class:`flask.Response`: 200, along with the booking data (empty if none found)
    """
    user_id = request.args.get('user_id')
    if user_id is None:  # Check if user_id is provided
        bookings = Booking.query.all()  # If no user_id provided, get all bookings in the database
    else:
        status = request.args.get('status')  # Get status from parameter
        if status is not None:  # If status is provided
            bookings = Booking.query.filter_by(completed=int(status)).join(User).filter(User.username == user_id)
            # booking of user with user_id and status is status
        else:
            bookings = Booking.query.join(User).filter(User.username == user_id)  # If no status is provided,
            # retrieve all booking of user with user_id
    data = json.loads(BookingSchema(many=True).dumps(bookings))
    for booking in data:
        booking['start'] = booking['start'].replace("T", " ")
        booking['end'] = booking['end'].replace("T", " ")
    return Response(json.dumps(data), status=200, mimetype="application/json")


@api.route("/booking", methods=['GET'])
def get_booking():
    """Returns a booking for a corresponding booking id

    Args:
        booking_id: id of booking (int)

    Returns:
        :class:`flask.Response`: 200 if successful, along with booking data as a json object, 400 if params missing
        (booking_id), 404 if booking id is invalid: not in database
    """
    booking_id = request.args.get('booking_id')
    if booking_id is not None:  # Check if booking_id is provided
        booking = Booking.query.get(booking_id)  # Retrieve booking with booking_id
        if booking is not None:
            return Response(BookingSchema().dumps(booking), status=200, content_type="application/json")
        else:
            return Response("invalid booking id", status=404)
    return Response("missing booking_id argument", status=400)


@api.route("/booking", methods=['POST'])
def add_booking():
    """Adds a booking to the database

    Args:
        booking data: a json object

    Returns:
        :class:`flask.Response`: 200 if successful, along with booking id, 400 if invalid: overlapped with existing
        bookings, 400 if invalid/missing params, or invalid json structure
    """
    request_data = request.get_json()  # Get booking data from parameter
    if request_data is not None:
        try:
            data = json.loads(request_data)
        except JSONDecodeError:
            return Response("Invalid json data received", status=400)
        if User.query.get(data['user_id']) is None:
            return Response("User is not in database", status=404)
        booking = Booking()  # Create booking object and add booking data
        booking.start = datetime.strptime(data['start'], "%Y-%m-%d %H:%M:%S")
        booking.end = datetime.strptime(data['end'], "%Y-%m-%d %H:%M:%S")
        booking.user_id = data['user_id']
        booking.car_id = data['car_id']
        booking.completed = 0
        booking.cost = calc_cost(float(data['cph']), booking.start, booking.end)
        booking.booking_date = datetime.now()
        if data['event_id'] is not None:  # If event_id is provided, add event_id to booking
            booking.event_id = data['event_id']
        if valid_booking(booking):  # Check if booking is valid
            db.session.add(booking)  # Add booking to database
            db.session.commit()
            return Response(json.dumps({"booking_id": booking.booking_id}), status=200, mimetype="application/json")
        else:
            return Response("Invalid booking: dates overlap with an existing booking", status=400)
    return Response("Invalid request data", status=400)


def calc_cost(amount: float, start: datetime, end: datetime) -> float:
    """Calculates the cost for a booking

    Args:
        amount: cph value for the car
        start: booking start date
        end: booking end date

    Returns:
        float value representing the total cost for a trip
    """
    return float("{:.2f}".format(amount * calc_hours(d1=start, d2=end)))


def valid_booking(proposed: Booking) -> bool:
    """Validates on server whether proposed booking overlaps any existing bookings for the vehicle

    Args:
        proposed: a proposed booking record (new booking)

    Returns:
        a boolean value: True if the proposed booking has no overlaps, otw false
    """
    existing_bookings = Booking.query.filter_by(car_id=proposed.car_id).filter_by(completed=0)  # get all bookings car
    for booking in existing_bookings:  # compare proposed booking against existing bookings
        if compare_dates(d_start=proposed.start, d_end=proposed.end, b_start=booking.start, b_end=booking.end):
            return False
    return True


@api.route("/booking", methods=['PUT'])
def update_booking():
    """Update a booked booking status: cancelled

    Args:
        booking data: in the form of a json object

    Returns:
        :class:`flask.Response`: 200 if successful, and booking data as a json object, 400 if invalid json data received
         in request, 404 if booking id was invalid: not in database
    """
    data = request.get_json()
    response = None
    if data is not None:
        json_data = json.loads(data)
        booking_id = json_data['booking_id']
        if booking_id is not None:  # Check if booking_id is provided
            booking = Booking.query.get(booking_id)  # Retrieve booking with booking id
            if booking is not None:
                booking.completed = 2  # Update booking status = cancelled
                db.session.commit()
                b_data = json.loads(BookingSchema().dumps(booking))
                response = Response(
                    json.dumps(
                        {
                            'car_id': b_data["car_id"],
                            'start': b_data["start"].replace("T", " "),
                            'end': b_data["end"].replace("T", " ")
                        }
                    ), status=200, mimetype='application/json')  # Return booking object
            else:
                response = Response("Invalid BookingID", status=404)
    else:
        response = Response("Invalid JSON received in request", status=400)
    return response


@api.route("/eventId", methods=['PUT'])
def update_eventId():
    """Update eventid (used to identify google calendar event) for booking

    Args:
        booking data: in the form of a json object

    Returns:
        Success if processed correctly, otherwise error corresponding to the problem
    """
    data = request.get_json()
    response = {}
    if data is not None:
        json_data = json.loads(data)
        event_id = json_data['event_id']
        booking_id = json_data['booking_id']
        if None not in (event_id, booking_id):  # Check if event_id and booking_id are provided
            booking = Booking.query.get(booking_id)  # Retrieve booking with booking_id
            if booking is not None:
                booking.event_id = event_id  # Add event_id to booking object
                db.session.commit()
                response['code'] = 'SUCCESS'
                response['data'] = {
                    'car_id': booking.car_id,
                    'start': booking.start,
                    'end': booking.end,
                    'event_id': booking.event_id
                }
            else:
                response['code'] = 'BOOKING ERROR'
                response['data'] = 'Invalid BookingID'
    else:
        response['code'] = "JSON ERROR"
        response['data'] = 'Invalid JSON received.'
    return response


# noinspection DuplicatedCode
@api.route("/populate", methods=['GET'])
def populate():
    """populates database with dummy data using csv files (see test_data directory).

    Returns:
        json object noting if a table was populated (boolean value)
    """
    response = {}
    if User.query.first() is None:
        with open('./test_data/user.csv') as users:
            reader = csv.reader(users, delimiter=',')
            for row in reader:
                print(row)
                user = User()
                user.username = row[0]
                user.email = row[1]
                user.f_name = row[2]
                user.l_name = row[3]
                salt = get_random_alphaNumeric_string(10)
                user.password = hash_password(row[4], salt) + ':' + salt
                user.register_date = row[5]
                user.face_id = False
                db.session.add(user)
            response['users'] = True
    if Employee.query.first() is None:
        with open("./test_data/employee.csv") as employees:
            reader = csv.reader(employees, delimiter=',')
            for row in reader:
                print(row)
                employee = Employee()
                employee.username = row[0]
                employee.email = row[1]
                employee.f_name = row[2]
                employee.l_name = row[3]
                salt = get_random_alphaNumeric_string(10)
                employee.password = hash_password(row[4], salt) + ':' + salt
                employee.type = row[5]
                db.session.add(employee)
            response['employees'] = True
    if CarModel.query.first() is None:
        model_ids = []
        with open('./test_data/car_model.csv') as models:
            reader = csv.reader(models, delimiter=',')
            for row in reader:
                print(row)
                model = CarModel()
                model.id = row[0]
                model_ids.append(row[0])
                model.make = row[1]
                model.model = row[2]
                model.year = row[3]
                model.capacity = row[4]
                model.colour = row[5]
                model.transmission = row[6]
                model.weight = row[7]
                model.length = row[8]
                model.load_index = row[9]
                model.engine_capacity = row[10]
                model.ground_clearance = row[11]
                db.session.add(model)
            response['models'] = True
        # car_cols = ['car_id', 'name', 'cph', 'lat', 'lng']
        if Car.query.first() is not None:
            Car.query.delete()
        car_ids = []
        with open('./test_data/car.csv') as cars:
            reader = csv.reader(cars, delimiter=',')
            i = 0
            for row in reader:
                print(row)
                car = Car()
                car_ids.append(row[0])
                car.car_id = row[0]
                car.model_id = model_ids[i]
                car.name = row[1]
                car.cph = row[2]
                car.lat = row[3]
                car.lng = row[4]
                car.locked = 1
                db.session.add(car)
                i += 1
            response['cars'] = True
        if CarReport.query.first() is not None:
            CarReport.query.delete()
        with open('./test_data/car_report.csv') as reports:
            reader = csv.reader(reports, delimiter=',')
            i = 0
            for row in reader:
                print(row)
                report = CarReport()
                report.car_id = car_ids[i]
                report.details = row[1]
                report.report_date = row[2]
                report.priority = row[3]
                db.session.add(report)
                i += 1
            response['reports'] = True
        with open('./test_data/booking.csv') as bookings:
            reader = csv.reader(bookings, delimiter=',')
            for row in reader:
                print(row)
                booking = Booking()
                booking.car_id = row[0]
                booking.user_id = row[1]
                booking.start = datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S")
                booking.end = datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S")
                booking.booking_date = datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S")
                booking.cost = calc_cost(float(row[5]), booking.start, booking.end)
                booking.completed = 1
                db.session.add(booking)
            response['bookings'] = True
    db.session.commit()
    return response
