import sys
from model.Vaccine import Vaccine
from model.Caregiver import Caregiver
from model.Patient import Patient
from util.Util import Util
from db.ConnectionManager import ConnectionManager
import pymssql
import datetime
from random import choice
import uuid
import pandas as pd


'''
objects to keep track of the currently logged-in user
Note: it is always true that at most one of currentCaregiver and currentPatient is not null
        since only one user can be logged-in at a time
'''
current_patient = None

current_caregiver = None

front_username = "Log in/Sign up"


def create_patient(tokens):
    # create_patient <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    username = tokens[1]
    password = tokens[2]
    # check 2: check if the username has been taken already
    if username_exists_patient(username):
        print("Username taken, try again!")
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the patient
    try:
        patient = Patient(username, salt=salt, hash=hash)
        # save to caregiver information to our database
        patient.save_to_db()
        print(" *** Patient Account created successfully *** ")
    except pymssql.Error:
        print("Create failed")
        return


def create_caregiver(tokens):
    # create_caregiver <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    username = tokens[1]
    password = tokens[2]
    # check 2: check if the username has been taken already
    if username_exists_caregiver(username):
        print("Username taken, try again!")
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the caregiver
    try:
        caregiver = Caregiver(username, salt=salt, hash=hash)
        # save to caregiver information to our database
        caregiver.save_to_db()
        print(" *** Caregiver Account created successfully *** ")
    except pymssql.Error:
        print("Create failed")
        return


def username_exists_caregiver(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is None
    except pymssql.Error:
        print("Error occurred when checking username")
        cm.close_connection()
    cm.close_connection()
    return False


def username_exists_patient(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Patients WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is None
    except pymssql.Error:
        print("Error occurred when checking username")
        cm.close_connection()
    cm.close_connection()
    return False


def login_patient(tokens):
    """
    TODO: Part 1
    """
    # login_patient <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_patient
    global front_username
    if current_patient is not None or current_caregiver is not None:
        print("Already logged-in!")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    username = tokens[1]
    password = tokens[2]

    patient = None
    try:
        patient = Patient(username, password=password).get()
    except pymssql.Error:
        print("Error occurred when logging in")

    # check if the login was successful
    if patient is None:
        print("Please try again!")
    else:
        print("Patient logged in as: " + username)
        current_patient = patient
        front_username = patient.username


def login_caregiver(tokens):
    # login_caregiver <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_caregiver
    global front_username
    if current_caregiver is not None or current_patient is not None:
        print("Already logged-in!")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    username = tokens[1]
    password = tokens[2]

    caregiver = None
    try:
        caregiver = Caregiver(username, password=password).get()
    except pymssql.Error:
        print("Error occurred when logging in")

    # check if the login was successful
    if caregiver is None:
        print("Please try again!")
    else:
        print("Caregiver logged in as: " + username)
        current_caregiver = caregiver
        front_username = caregiver.username


def search_caregiver_schedule(tokens):
    # search_caregiver_schedule <date>
    global current_caregiver
    global current_patient
    c_lst = []  # caregiver name list
    # check 1: if someone's logged-in
    if current_caregiver is None and current_patient is None:
        print("Please login first")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        return
    # check 3: assume input is hyphenated in the format mm-dd-yyyy, check if the date is valid
    date_tokens = tokens[1].split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)

    try:
        d_caregiver = datetime.datetime(year, month, day)
        view_caregiver = "SELECT Username FROM Availabilities WHERE Time = %s;"

        cursor.execute(view_caregiver, d_caregiver)
        print("available caregiver:")

        for row in cursor:
            c_lst.append(row['Username'])

        # check 4: if the caregiver is available on the selected date
        if c_lst:
            c_ava_df = pd.DataFrame(c_lst, columns=['available caregiver'])
            print(c_ava_df)
            return c_lst
        else:
            print("No caregiver is available on "+str(d_caregiver.strftime('%Y-%m-%d'))+". Please choose another day")
            return False
        # you must call commit() to persist your data if you don't set autocommit to True
        conn.commit()
    except ValueError:
        print("Please enter a valid date! Format as mm-dd-yyyy")
    except pymssql.Error:
        print("Error occurred when searching Caregiver")
        cm.close_connection()
    cm.close_connection()


def reserve(tokens):
    # reserve <date> <vaccine>
    # check 1: if the patient is logged in
    global current_patient
    if current_patient is None:
        print("Please log in as Patient")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information
    if len(tokens) != 3:
        print("Please try again!")
        return

    # check 3: if the date is valid
    reserve_date = tokens[1].split("-")
    month = int(reserve_date[0])
    day = int(reserve_date[1])
    year = int(reserve_date[2])
    try:
        reserve_date = datetime.datetime(year, month, day)
    except ValueError:
        print("Please enter a valid date! Format as mm-dd-yyyy")
        return
    # check 4: if the vaccine is available
    vaccine_name = tokens[2]
    doses = 1
    vaccine = Vaccine(vaccine_name, doses).get()
    if vaccine is None:
        print("Can NOT find "+vaccine_name+" in database")
        return

    # check 5: if the vaccine has enough doses
    if vaccine.available_doses<=0:
        print(vaccine_name + " is out of stock")
        return

    # check 6: check if any caregiver is available on this day
    c_lst = search_caregiver_schedule(tokens[0:2])
    if not c_lst:
        return
    # print("Available doses left "+str(vaccine.available_doses)+" in stock")

    # uuid
    try:
        caregiver_name_random = choice(c_lst)
        print("Your caregiver is: " + caregiver_name_random)
        mix_id = reserve_date.strftime('%Y%m%d') + current_patient.username
        appointment_id = uuid.uuid5(uuid.NAMESPACE_DNS, mix_id)
        print("Your username is: " + str(current_patient.username))
    except ValueError:
        print("Error occurred when validation")

    # Check 7: check for confirmation
    while True:
        print("Confirm: One dose of ["+vaccine_name+"] on ["+reserve_date.strftime('%Y-%m-%d')+"]")
        in_content = input("Confirm? [y/n]：")
        if in_content == "y":

            # Check 9: check if appointment exists
            try:
                cm = ConnectionManager()
                conn = cm.create_connection()
                cursor = conn.cursor()
                check_appointment = "SELECT * FROM Reserve WHERE appointment_id = %s"
                cursor.execute(check_appointment, str(appointment_id))
                if cursor.fetchone() is not None:
                    print("Your appointment already exists")
                    return
                # conn.commit()
                # cm.close_connection()
            except pymssql.Error:
                print("Error occurred when validation_username")

            try:
                # add appointment
                add_appointment = "INSERT INTO Reserve VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(add_appointment, (
                    appointment_id, reserve_date, vaccine_name, current_patient.username, caregiver_name_random))

                # delete availabilities of caregiver
                delete_availability = "DELETE FROM Availabilities WHERE Time = %s AND Username = %s"
                cursor.execute(delete_availability, (reserve_date, caregiver_name_random))
                # you must call commit() to persist your data if you don't set autocommit to True
                conn.commit()
                cm.close_connection()
                vaccine.decrease_available_doses(1)
                print("Available doses left " + str(vaccine.available_doses) + " in stock")
                print("Successful appointment！")
            except pymssql.Error:
                print("Error occurred when add appointment/delete caregiver availabilities")
            return
        elif in_content == "n":
            print("Exit appointment")
            return
        else:
            print("Please try again")


def upload_availability(tokens):
    #  upload_availability <date>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        return

    date = tokens[1]
    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    try:
        d = datetime.datetime(year, month, day)
        # check if caregiver already exist on date
        check_exist = "SElECT * FROM Availabilities WHERE Time = %s AND Username = %s"
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(check_exist, (d, current_caregiver.get_username()))
            ava_lst = cursor.fetchone()
            if ava_lst is not None:
                print("Caregiver exists on this date")
                return
        except pymssql.Error:
            print("Error occurred when checking caregiver availability")
            cm.close_connection()
        # continue uploading
        current_caregiver.upload_availability(d)
        print("Availability uploaded!")
    except ValueError:
        print("Please enter a valid date! Format as mm-dd-yyyy")
    except pymssql.Error as db_err:
        print("Error occurred when uploading availability")


def cancel(tokens):
    # check 1: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        return

    # check 2: check login
    if current_caregiver is None and current_patient is None:
        print("Please login first")
        return
    # check 3: Did not check if the user has access to cancel appointment. because every user can only access their own appointment and the appointment_id is unique
    # fetch appointment info
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)
    get_all = "SELECT * FROM Reserve WHERE appointment_id = %s"
    # get_vaccine_name = "SELECT Vaccine_name FROM Reserve WHERE appointment_id = %s"
    try:
        cursor.execute(get_all, tokens[1])
        for row in cursor:
            vaccine_name = row['Vaccine_name']
            username = row['C_Username']
            r_date = row['Time']
        conn.commit()
    except pymssql.Error:
        print("Error occurred when fetching information from appointments")
        cm.close_connection()

    # recall vaccine
    try:
        doses = 1
        vaccine = Vaccine(vaccine_name, doses).get()
        vaccine.increase_available_doses(1)
    except pymssql.Error:
        print("Error occurred when recall doses")
        cm.close_connection()

    # recall availabilities of caregivers
    try:
        caregiver = Caregiver(username)
        caregiver.upload_availability(r_date)
    except pymssql.Error:
        print("Error occurred when recall availability")
        cm.close_connection()
    cm.close_connection()

    # delete appointment
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()
    cancel_appointments = "DELETE FROM Reserve WHERE appointment_id = %s"
    try:
        cursor.execute(cancel_appointments, tokens[1])
        conn.commit()
    except pymssql.Error:
        print("Error occurred when cancel caregiver appointment")
        cm.close_connection()

    print("Successfully cancel your appointment")
    cm.close_connection()


def add_doses(tokens):
    #  add_doses <vaccine> <number>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    #  check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    vaccine_name = tokens[1]
    doses = int(tokens[2])
    vaccine = None
    try:
        vaccine = Vaccine(vaccine_name, doses).get()
    except pymssql.Error:
        print("Error occurred when adding doses")

    # check 3: if getter returns null, it means that we need to create the vaccine and insert it into the Vaccines
    #          table

    if vaccine is None:
        try:
            vaccine = Vaccine(vaccine_name, doses)
            vaccine.save_to_db()
        except pymssql.Error:
            print("Error occurred when adding doses")
    else:
        # if the vaccine is not null, meaning that the vaccine already exists in our table
        try:
            vaccine.increase_available_doses(doses)
        except pymssql.Error:
            print("Error occurred when adding doses")

    print("Doses updated!")


def show_appointments(tokens):
    # check 1: the length for tokens need to be exactly 1 to include all information (with the operation name)
    if len(tokens) != 1:
        print("Please try again!")
        return

    # check 2: login
    if current_caregiver is None and current_patient is None:
        print("Please login first")
        return
    # check 3: identity: caregiver vs patient
    if current_patient is None:
        # caregiver logged in
        c_username = current_caregiver.username
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor(as_dict=True)
        show_appointments_caregiver = "SELECT appointment_id, Time, Vaccine_name, P_Username FROM Reserve WHERE C_Username = %s"
        try:
            cursor.execute(show_appointments_caregiver, current_caregiver.username)
            ans = cursor.fetchall()
            c_appoint_df = pd.DataFrame(ans)
            if c_appoint_df.empty:
                print("No appointments")
                return
            print(c_appoint_df)
            # you must call commit() to persist your data if you don't set autocommit to True
            conn.commit()
        except pymssql.Error:
            print("Error occurred when fetching caregiver appointment")
            cm.close_connection()
        cm.close_connection()
    else:
        # patient logged in
        p_username = current_patient.username
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor(as_dict=True)
        show_appointments_patient = "SELECT appointment_id, Time, Vaccine_name, C_Username FROM Reserve WHERE P_Username = %s"
        try:
            cursor.execute(show_appointments_patient, current_patient.username)
            ans = cursor.fetchall()
            p_appoint_df = pd.DataFrame(ans)
            if p_appoint_df.empty:
                print("No appointments")
                return
            print(p_appoint_df)
            # you must call commit() to persist your data if you don't set autocommit to True
            conn.commit()
        except pymssql.Error:
            print("Error occurred when fetching patient appointment")
            cm.close_connection()
        cm.close_connection()


def logout(tokens):
    global current_patient
    global current_caregiver
    global front_username
    try:
        if current_patient is not None or current_caregiver is not None:
            current_patient = None
            current_caregiver = None
            print("Successfully logged out!")
            front_username = "Log in/Sign up"
        else:
            print("Please login first!")
    except ValueError:
        print("Error occurred when logging out")


def start():
    stop = False
    while not stop:
        print()
        print("Hello " + front_username)
        print(" *** Please enter one of the following commands *** ")
        print("> create_patient <username> <password>")  # //TODO: implement create_patient (Part 1)
        print("> create_caregiver <username> <password>")
        print("> login_patient <username> <password>")  #// TODO: implement login_patient (Part 1)
        print("> login_caregiver <username> <password>")
        print("> search_caregiver_schedule <date>")  #// TODO: implement search_caregiver_schedule (Part 2)
        print("> reserve <date> <vaccine>") #// TODO: implement reserve (Part 2)
        print("> upload_availability <date>")
        print("> cancel <appointment_id>") #// TODO: implement cancel (extra credit)
        print("> add_doses <vaccine> <number>")
        print("> show_appointments")  #// TODO: implement show_appointments (Part 2)
        print("> logout") #// TODO: implement logout (Part 2)
        print("> Quit")
        print()
        response = ""
        print("> Enter: ", end='')

        try:
            response = str(input())
        except ValueError:
            print("Type in a valid argument")
            break

        response = response.lower()
        tokens = response.split(" ")
        if len(tokens) == 0:
            ValueError("Try Again")
            continue
        operation = tokens[0]
        if operation == "create_patient":
            create_patient(tokens)
        elif operation == "create_caregiver":
            create_caregiver(tokens)
        elif operation == "login_patient":
            login_patient(tokens)
        elif operation == "login_caregiver":
            login_caregiver(tokens)
        elif operation == "search_caregiver_schedule":
            search_caregiver_schedule(tokens)
        elif operation == "reserve":
            reserve(tokens)
        elif operation == "upload_availability":
            upload_availability(tokens)
        elif operation == 'cancel':
            cancel(tokens)
        elif operation == "add_doses":
            add_doses(tokens)
        elif operation == "show_appointments":
            show_appointments(tokens)
        elif operation == "logout":
            logout(tokens)
        elif operation == "quit":
            print("Thank you for using the scheduler, Goodbye!")
            stop = True
        else:
            print("Invalid Argument")


if __name__ == "__main__":
    '''
    // pre-define the three types of authorized vaccines
    // note: it's a poor practice to hard-code these values, but we will do this ]
    // for the simplicity of this assignment
    // and then construct a map of vaccineName -> vaccineObject
    '''

    # start command line
    print()
    print("Welcome to the COVID-19 Vaccine Reservation Scheduling Application!")

    start()
