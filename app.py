import sqlite3
from datetime import datetime, timedelta
import threading
import time


conn = sqlite3.connect('library.db')
cursor = conn.cursor()


cursor.executescript("""

CREATE TABLE IF NOT EXISTS User (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    password TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS Book (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    genre TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT NOT NULL,
    returning_date DATE
);


CREATE TABLE IF NOT EXISTS StudyGroup (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre TEXT DEFAULT 'General',
    name TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS GroupMember (
    group_id INTEGER,
    user_id INTEGER,
    FOREIGN KEY (group_id) REFERENCES StudyGroup(group_id),
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);


CREATE TABLE IF NOT EXISTS RoomReservation (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number INTEGER NOT NULL,
    reserved_by TEXT NOT NULL,
    time_slot TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS BorrowedBook (
    borrow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER,
    user_id INTEGER,
    borrow_date DATE NOT NULL,
    due_date DATE NOT NULL,
    FOREIGN KEY (book_id) REFERENCES Book(book_id),
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);
""")
conn.commit()


class User:
    def __init__(self, user_id=None, name=None, email=None, password=None):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password

    def register(self):
        name = input("Enter your name: ").strip()
        email = input("Enter your email: ").strip()
        password = input("Enter your password: ").strip()


        try:
            cursor.execute(
                "INSERT INTO User (name, email, password) VALUES (?, ?, ?)",
                (name, email, password),
            )
            conn.commit()
            print("Registration successful!")
        except sqlite3.IntegrityError:
            print("An account with this email already exists.")

    @staticmethod
    def login(email, password):
        cursor.execute("SELECT * FROM User WHERE email = ? AND password = ?", (email, password))
        user_data = cursor.fetchone()
        return User(*user_data) if user_data else None

class Book:
    def __init__(self, book_id=None, title=None, genre=None, author=None, status="Available", returning_date=None):
        self.book_id = book_id
        self.title = title
        self.genre = genre
        self.author = author
        self.status = status
        self.returning_date = returning_date

    def add_to_db(self):
        cursor.execute("INSERT INTO Book (title, genre, author, status, returning_date) VALUES (?, ?, ?, ?, ?)",
                       (self.title, self.genre, self.author, self.status, self.returning_date))
        conn.commit()
        self.book_id = cursor.lastrowid
        print("Book added successfully!")

    @staticmethod
    def list_books():
        cursor.execute("SELECT * FROM Book")
        books = cursor.fetchall()
        if not books:
            print("No books found.")
        else:
            for book in books:
                print(f"ID: {book[0]}, Title: {book[1]}, Genre: {book[2]}, Author: {book[3]}, Status: {book[4]}")

    def borrow(self, user_id):
        if self.status == "Available":
            self.status = "Borrowed"
            borrow_date = datetime.now().strftime('%Y-%m-%d')
            due_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
            cursor.execute("UPDATE Book SET status = ?, returning_date = ? WHERE book_id = ?", 
                           (self.status, due_date, self.book_id))
            cursor.execute("INSERT INTO BorrowedBook (book_id, user_id, borrow_date, due_date) VALUES (?, ?, ?, ?)", 
                           (self.book_id, user_id, borrow_date, due_date))
            conn.commit()
            print(f"Book '{self.title}' borrowed successfully!")
        else:
            print(f"Book '{self.title}' is not available.")

    @staticmethod
    def return_book(book_id, user_id):
        cursor.execute("SELECT * FROM BorrowedBook WHERE book_id = ? AND user_id = ?", (book_id, user_id))
        borrowed = cursor.fetchone()
        if borrowed:
            due_date = datetime.strptime(borrowed[4], '%Y-%m-%d') 
            now = datetime.now()
            overdue_days = (now - due_date).days 

           
            if overdue_days > 0:
                fine = overdue_days * 2 
                print(f"The book is {overdue_days} day(s) overdue. You owe a fine of ${fine}.")
            else:
                print("The book is returned on time. No fine applicable.")

            
            cursor.execute("UPDATE Book SET status = 'Available', returning_date = NULL WHERE book_id = ?", (book_id,))
            cursor.execute("DELETE FROM BorrowedBook WHERE book_id = ? AND user_id = ?", (book_id, user_id))
            conn.commit()
            print("Book returned successfully!")
        else:
            print("You have not borrowed this book or the book ID is incorrect.")


def form_study_group():
    """Allows a user to create a new study group with a genre."""
    group_name = input("Enter the name of the study group: ").strip()
    genre = input("Enter the genre of the study group: ").strip()
    try:
        cursor.execute("INSERT INTO StudyGroup (name, genre) VALUES (?, ?)", (group_name, genre))
        conn.commit()
        print(f"Study group '{group_name}' with genre '{genre}' created successfully!")
    except sqlite3.Error as e:
        print(f"Error creating study group: {e}")

def show_all_study_groups():
    """Displays all the study groups along with their genres."""
    try:
        cursor.execute("SELECT * FROM StudyGroup")
        groups = cursor.fetchall()
        if groups:
            print("\nAvailable Study Groups:")
            for group in groups:
                print(f"Group ID: {group[0]}, Name: {group[1]}, Genre: {group[2]}")
        else:
            print("No study groups available.")
    except sqlite3.Error as e:
        print(f"Error fetching study groups: {e}")

def search_study_groups():
    """Allows users to search for study groups by genre."""
    genre = input("Enter the genre to search for study groups: ").strip()
    cursor.execute("SELECT * FROM StudyGroup WHERE genre LIKE ?", (f"%{genre}%",))
    groups = cursor.fetchall()
    if groups:
        print("\nMatching Study Groups:")
        for group in groups:
            print(f"Group ID: {group[0]}, Name: {group[1]}, Genre: {group[2]}")
    else:
        print("No study groups found for the specified genre.")

def join_study_group(user_id):
    """Allows a user to join an existing study group."""
    show_all_study_groups()
    try:
        group_id = int(input("Enter the ID of the study group you want to join: "))
        cursor.execute("SELECT * FROM StudyGroup WHERE group_id = ?", (group_id,))
        group = cursor.fetchone()
        if group:
            
            cursor.execute(
                "SELECT * FROM GroupMember WHERE group_id = ? AND user_id = ?",
                (group_id, user_id),
            )
            existing_member = cursor.fetchone()
            if existing_member:
                print("You are already a member of this group.")
            else:
                cursor.execute(
                    "INSERT INTO GroupMember (group_id, user_id) VALUES (?, ?)",
                    (group_id, user_id),
                )
                conn.commit()
                print(f"You have successfully joined the study group '{group[1]}'!")
        else:
            print("Invalid group ID. Please try again.")
    except ValueError:
        print("Invalid input. Please enter a valid group ID.")
    except sqlite3.Error as e:
        print(f"Error joining study group: {e}")

def save_record(table_name, **fields):
    try:
        columns = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields.values())
        values = tuple(fields.values())
        
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor.execute(query, values)
        conn.commit()
        print(f"Record successfully added to {table_name}.")
    except sqlite3.IntegrityError as e:
        print(f"Error saving record to {table_name}: {e}")  

def search_books():
    print("\nSearch for Books")
    print("1. Search by Title")
    print("2. Search by Genre")
    print("3. Search by Author")
    print("4. Return to Main Menu")
    
    choice = input("Enter your choice: ")
    
    if choice == "1":
        title = input("Enter the book title to search: ").strip()
        cursor.execute("SELECT * FROM Book WHERE title LIKE ?", (f"%{title}%",))
    elif choice == "2":
        genre = input("Enter the genre to search: ").strip()
        cursor.execute("SELECT * FROM Book WHERE genre LIKE ?", (f"%{genre}%",))
    elif choice == "3":
        author = input("Enter the author's name to search: ").strip()
        cursor.execute("SELECT * FROM Book WHERE author LIKE ?", (f"%{author}%",))
    elif choice == "4":
        return
    else:
        print("Invalid choice! Please try again.")
        return search_books()
    
    
    results = cursor.fetchall()
    if results:
        print("\nSearch Results:")
        for book in results:
            print(f"ID: {book[0]}, Title: {book[1]}, Genre: {book[2]}, Author: {book[3]}, Status: {book[4]}")
    else:
        print("\nNo books found matching your criteria.")

def leave_study_group(user_id):
    """Allows a user to leave a study group they are a member of."""
    try:
        
        cursor.execute("""
            SELECT sg.group_id, sg.name 
            FROM StudyGroup sg
            INNER JOIN GroupMember gm ON sg.group_id = gm.group_id
            WHERE gm.user_id = ?
        """, (user_id,))
        groups = cursor.fetchall()

        if not groups:
            print("You are not a member of any study groups.")
            return

        print("\nYour Study Groups:")
        for group in groups:
            print(f"Group ID: {group[0]}, Name: {group[1]}")

        
        group_id = int(input("Enter the ID of the group you want to leave: "))
        cursor.execute("SELECT * FROM GroupMember WHERE group_id = ? AND user_id = ?", (group_id, user_id))
        membership = cursor.fetchone()

        if membership:
            cursor.execute("DELETE FROM GroupMember WHERE group_id = ? AND user_id = ?", (group_id, user_id))
            conn.commit()
            print("You have successfully left the study group.")
        else:
            print("Invalid group ID or you are not a member of the selected group.")
    except ValueError:
        print("Invalid input. Please enter a valid group ID.")
    except sqlite3.Error as e:
        print(f"Error leaving study group: {e}")


def reserve_room(user_name):
    """
    Allows a user to reserve a room with a specific time slot.
    Ensures the room number is between 1 and 10.
    """
    try:
        room_number = int(input("Enter the room number to reserve (1–10): "))
        
       
        if room_number < 1 or room_number > 10:
            print("Invalid room number. Please choose a room number between 1 and 10.")
            return
        
        time_slot = input("Enter the time slot for reservation (e.g., 10:00 AM - 12:00 PM): ").strip()
        
        
        cursor.execute(
            "SELECT * FROM RoomReservation WHERE room_number = ? AND time_slot = ?",
            (room_number, time_slot)
        )
        reservation = cursor.fetchone()

        if reservation:
            print("This room is already reserved for the given time slot. Please choose another slot.")
        else:
            
            cursor.execute(
                "INSERT INTO RoomReservation (room_number, reserved_by, time_slot) VALUES (?, ?, ?)",
                (room_number, user_name, time_slot)
            )
            conn.commit()
            print(f"Room {room_number} successfully reserved for {time_slot}.")
    except ValueError:
        print("Invalid input. Please enter valid details.")
    except sqlite3.Error as e:
        print(f"Error reserving room: {e}")

def reset_room_reservations():
    """
    Resets all room reservations at the end of the day.
    Clears the RoomReservation table.
    """
    try:
        cursor.execute("DELETE FROM RoomReservation")
        conn.commit()
        print("All room reservations have been reset.")
    except sqlite3.Error as e:
        print(f"Error resetting room reservations: {e}")

def schedule_reset():
    """
    Continuously checks the time and resets room reservations at midnight.
    """
    while True:
        now = datetime.now()
        
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_until_reset = (next_midnight - now).total_seconds()
        
        
        time.sleep(time_until_reset)
        
        
        reset_room_reservations()

def show_reservations():
    """
    Displays all current room reservations.
    """
    try:
        cursor.execute("SELECT * FROM RoomReservation")
        reservations = cursor.fetchall()

        if reservations:
            print("\nCurrent Room Reservations:")
            for reservation in reservations:
                print(f"Reservation ID: {reservation[0]}, Room Number: {reservation[1]}, Reserved By: {reservation[2]}, Time Slot: {reservation[3]}")
        else:
            print("No room reservations found.")
    except sqlite3.Error as e:
        print(f"Error fetching reservations: {e}")

def cancel_room_reservation(user_name):
    """
    Allows a user to cancel their room reservation.
    """
    try:
        
        cursor.execute(
            "SELECT reservation_id, room_number, time_slot FROM RoomReservation WHERE reserved_by = ?",
            (user_name,)
        )
        reservations = cursor.fetchall()

        if not reservations:
            print("You have no room reservations to cancel.")
            return

        
        print("\nYour Room Reservations:")
        for reservation in reservations:
            print(f"Reservation ID: {reservation[0]}, Room Number: {reservation[1]}, Time Slot: {reservation[2]}")

        
        reservation_id = int(input("Enter the Reservation ID of the reservation you want to cancel: "))
        cursor.execute(
            "SELECT * FROM RoomReservation WHERE reservation_id = ? AND reserved_by = ?",
            (reservation_id, user_name)
        )
        reservation = cursor.fetchone()

        if reservation:
            
            cursor.execute("DELETE FROM RoomReservation WHERE reservation_id = ?", (reservation_id,))
            conn.commit()
            print("Room reservation canceled successfully.")
        else:
            print("Invalid Reservation ID or you are not the owner of this reservation.")

    except ValueError:
        print("Invalid input. Please enter a valid Reservation ID.")
    except sqlite3.Error as e:
        print(f"Error canceling room reservation: {e}")



def main_menu():
    print("\nLibrary Management System")
    print("1. Register")
    print("2. Login")
    print("3. Add a Book")
    print("4. List All Books")
    print("5. Borrow a Book")
    print("6. Return a Book")
    print("7. Search for a Book")
    print("8. Form a Study Group")
    print("9. Show All Study Groups")
    print("10. Join a Study Group")
    print("11. Leave a Study Group")
    print("12. Search for Study Groups by Genre")
    print("13. Reserve a Room")
    print("14. Cancel Room Reservation")  
    print("15. Show Room Reservations")
    print("16. Exit")




    

def interactive_system():
    user = None

    # reset_thread = threading.Thread(target=schedule_reset, daemon=True)
    # reset_thread.start()

    while True:
        main_menu()
        choice = input("Enter your choice: ")

        if choice == "1":  
            user = User()
            user.register()

        elif choice == "2":  
            email = input("Enter your email: ")
            password = input("Enter your password: ")
            user = User.login(email, password)
            if user:
                print(f"Welcome back, {user.name}!")
            else:
                print("Invalid credentials!")

        elif choice == "3":  
            if user:
                title = input("Enter book title: ")
                genre = input("Enter book genre: ")
                author = input("Enter book author: ")
                book = Book(title=title, genre=genre, author=author)
                book.add_to_db()
            else:
                print("You need to log in as an administrator to add books.")

        elif choice == "4":  
            Book.list_books()

        elif choice == "5": 
            if user:
                Book.list_books()
                book_id = int(input("Enter the ID of the book you want to borrow: "))
                cursor.execute("SELECT * FROM Book WHERE book_id = ?", (book_id,))
                book_data = cursor.fetchone()
                if book_data:
                    book = Book(*book_data)
                    book.borrow(user.user_id)
                else:
                    print("Invalid book ID.")
            else:
                print("You need to log in to borrow books.")

        elif choice == "6":
            if user:
                book_id = int(input("Enter the ID of the book you want to return: "))
                Book.return_book(book_id, user.user_id)
            else:
                print("You need to log in to return books.")

        elif choice == "7": 
            search_books()

        elif choice == "8":  
            if user:
                form_study_group()
            else:
                print("You need to log in to form a study group.")

        elif choice == "9":
            show_all_study_groups()

        elif choice == "10":  
            if user:
                join_study_group(user.user_id)
            else:
                print("You need to log in to join a study group.")

        elif choice == "11": 
            if user:
                leave_study_group(user.user_id)
            else:
                print("You need to log in to leave a study group.")

        elif choice == "12": 
            search_study_groups()

        elif choice == "13": 
            if user:
                reserve_room(user.name)
            else:
                print("You need to log in to reserve a room.")

        elif choice == "14": 
            if user:
                cancel_room_reservation(user.name)
            else:
                print("You need to log in to cancel a room reservation.")


        elif choice == "15": 
            show_reservations()

        elif choice == "16":  
            conn.close()
            print("Thank you for using the Library Management System!")
            break

        else:
            print("Invalid choice. Please try again.")



if __name__ == "__main__":
    interactive_system()