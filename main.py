import tkinter as tk
from tkinter import messagebox, ttk
import cv2
import numpy as np
import csv
import os
import urllib.request
import urllib.parse
import json

# -----------------------------------------------------------------------
# Scanner library — zxing-cpp works on Windows without extra DLLs
# Install: pip install zxing-cpp
# Fallback: pyzbar (may need extra DLLs on Windows)
# -----------------------------------------------------------------------
try:
    import zxingcpp
    SCANNER_AVAILABLE = True
    SCANNER_NAME = "zxingcpp"
    print("[INFO] Using zxingcpp for barcode scanning")
except ImportError:
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        SCANNER_AVAILABLE = True
        SCANNER_NAME = "pyzbar"
        print("[INFO] Using pyzbar for barcode scanning")
    except ImportError:
        SCANNER_AVAILABLE = False
        SCANNER_NAME = None
        print("[WARNING] No barcode scanner library found! Install: pip install zxing-cpp")


def decode_barcodes(image_gray):
    results = []
    if not SCANNER_AVAILABLE:
        return results
    if SCANNER_NAME == "zxingcpp":
        detected = zxingcpp.read_barcodes(image_gray)
        for barcode in detected:
            text = barcode.text.strip()
            if text:
                results.append({"data": text, "rect": None})
    elif SCANNER_NAME == "pyzbar":
        detected = pyzbar_decode(image_gray)
        for barcode in detected:
            text = barcode.data.decode("utf-8").strip()
            if text:
                results.append({"data": text, "rect": barcode.rect})
    return results


CSV_FILE = 'books.csv'
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
GOOGLE_BOOKS_CATEGORY_API = "https://www.googleapis.com/books/v1/volumes?q=subject:{category}&maxResults=10"


class LibraryManagementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Library Book Scanner System")
        self.root.geometry("600x700")
        self.root.configure(bg="#f9f9f9")

        if not SCANNER_AVAILABLE:
            messagebox.showwarning(
                "Missing Dependency",
                "Barcode scanner library not found!\n\n"
                "Fix (Windows — Recommended):\n"
                "  pip install zxing-cpp\n\n"
                "Then restart the app.\n\n"
                "Barcode scanning will NOT work without it."
            )

        self.style = ttk.Style()
        self.style.configure("TLabel", font=("Arial", 12), background="#f9f9f9")
        self.style.configure("TButton", font=("Arial", 12))

        self.header = tk.Label(
            root, text="Library Book Scanner System",
            font=("Arial", 18, "bold"), bg="#f9f9f9", fg="#333333"
        )
        self.header.pack(pady=20)

        scanner_info = f"Scanner: {SCANNER_NAME}" if SCANNER_AVAILABLE else "Scanner: NOT AVAILABLE"
        self.scanner_label = tk.Label(
            root, text=scanner_info,
            font=("Arial", 9), bg="#f9f9f9",
            fg="green" if SCANNER_AVAILABLE else "red"
        )
        self.scanner_label.pack()

        self.camera_frame = tk.LabelFrame(
            root, text="Camera Source",
            font=("Arial", 12, "bold"), bg="#f9f9f9", fg="#333333", padx=10, pady=10
        )
        self.camera_frame.pack(pady=10, padx=20, fill="x")

        self.camera_source = tk.StringVar(value="webcam")

        self.webcam_radio = tk.Radiobutton(
            self.camera_frame, text="Webcam",
            variable=self.camera_source, value="webcam",
            bg="#f9f9f9", font=("Arial", 11),
            command=self.toggle_camera_options
        )
        self.webcam_radio.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.rtsp_radio = tk.Radiobutton(
            self.camera_frame, text="RTSP Camera",
            variable=self.camera_source, value="rtsp",
            bg="#f9f9f9", font=("Arial", 11),
            command=self.toggle_camera_options
        )
        self.rtsp_radio.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        self.webcam_index_label = tk.Label(
            self.camera_frame, text="Webcam Index:",
            bg="#f9f9f9", font=("Arial", 10)
        )
        self.webcam_index_label.grid(row=1, column=0, padx=10, pady=3, sticky="w")

        self.webcam_index_entry = ttk.Entry(self.camera_frame, width=5, font=("Arial", 11))
        self.webcam_index_entry.insert(0, "0")
        self.webcam_index_entry.grid(row=1, column=1, padx=5, pady=3, sticky="w")

        self.rtsp_url = "rtsp://arif:123456@10.194.133.40:1945/stream"

        self.scan_button = ttk.Button(
            root, text="Scan Barcode",
            command=self.start_scanning, style="Custom.TButton"
        )
        self.scan_button.pack(pady=20)

        self.result_label = tk.Label(
            root, text="", font=("Arial", 11), bg="#f9f9f9",
            fg="#333333", wraplength=550, justify="left"
        )
        self.result_label.pack(pady=10)

        self.view_total_books_button = ttk.Button(
            root, text="View Total Books", command=self.view_total_books
        )
        self.view_total_books_button.pack(pady=5)

        self.list_books_button = ttk.Button(
            root, text="List Books", command=self.list_books
        )
        self.list_books_button.pack(pady=5)

        self.add_book_button = ttk.Button(
            root, text="Add Book", command=self.add_book
        )
        self.add_book_button.pack(pady=5)

        self.close_button = ttk.Button(root, text="Close", command=root.quit)
        self.close_button.pack(pady=10)

    def toggle_camera_options(self):
        if self.camera_source.get() == "webcam":
            self.webcam_index_entry.config(state="normal")
        else:
            self.webcam_index_entry.config(state="disabled")

    def get_camera_source(self):
        if self.camera_source.get() == "webcam":
            try:
                return int(self.webcam_index_entry.get())
            except ValueError:
                messagebox.showerror("Input Error", "Webcam index must be a number.")
                return None
        else:
            return self.rtsp_url

    # -------------------------------------------------------------------------
    # Google Books API
    # -------------------------------------------------------------------------

    def fetch_book_info_from_api(self, isbn):
        try:
            url = GOOGLE_BOOKS_API.format(isbn=isbn)
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())

            if data.get("totalItems", 0) == 0:
                return None

            volume_info = data["items"][0]["volumeInfo"]

            title       = volume_info.get("title", "Unknown Title")
            authors     = volume_info.get("authors", ["Unknown Author"])
            categories  = volume_info.get("categories", ["Unknown"])
            publisher   = volume_info.get("publisher", "Unknown Publisher")
            published   = volume_info.get("publishedDate", "N/A")
            description = volume_info.get("description", "No description available.")
            thumbnail   = volume_info.get("imageLinks", {}).get("thumbnail", None)

            return {
                "title":         title,
                "authors":       ", ".join(authors),
                "category":      categories[0] if categories else "Unknown",
                "publisher":     publisher,
                "publishedDate": published,
                "description":   description,
                "thumbnail":     thumbnail,
            }

        except Exception as e:
            print(f"[API Error] {e}")
            return None

    def fetch_recommendations_from_api(self, category, current_title):
        recommendations = []
        try:
            url = GOOGLE_BOOKS_CATEGORY_API.format(category=urllib.parse.quote(category))
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())

            for item in data.get("items", []):
                rec_title = item["volumeInfo"].get("title", "")
                if rec_title and rec_title != current_title:
                    recommendations.append(rec_title)
                if len(recommendations) >= 3:
                    break

        except Exception as e:
            print(f"[Recommendation API Error] {e}")

        return recommendations

    # -------------------------------------------------------------------------
    # ✅ NEW: Save scanned book to CSV (with duplicate check)
    # -------------------------------------------------------------------------

    def save_book_to_csv(self, barcode, book_info):
        """Saves a scanned book to the CSV file, skipping duplicates silently."""
        # Check for duplicate barcode
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('barcode') == barcode:
                        print(f"[CSV] Barcode '{barcode}' already exists — skipping save.")
                        return False  # Already exists, skip

        file_exists = os.path.exists(CSV_FILE)
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
            fieldnames = ['title', 'barcode', 'genre', 'author', 'publisher']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                'title':     book_info.get('title', ''),
                'barcode':   barcode,
                'genre':     book_info.get('category', ''),
                'author':    book_info.get('authors', ''),
                'publisher': f"{book_info.get('publisher', '')} ({book_info.get('publishedDate', '')})",
            })

        print(f"[CSV] Saved: '{book_info.get('title')}' with barcode '{barcode}'")
        return True

    # -------------------------------------------------------------------------
    # Preprocessing — multiple variants for better detection
    # -------------------------------------------------------------------------

    def get_preprocessed_variants(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        variants = [
            gray,
            cv2.equalizeHist(gray),
            cv2.filter2D(gray, -1,
                         np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])),
            cv2.resize(gray, (gray.shape[1] * 2, gray.shape[0] * 2),
                       interpolation=cv2.INTER_LINEAR),
        ]
        return variants

    # -------------------------------------------------------------------------
    # Main Scanning Loop
    # -------------------------------------------------------------------------

    def start_scanning(self):
        if not SCANNER_AVAILABLE:
            messagebox.showerror(
                "Scanner Not Available",
                "No barcode library installed!\n\n"
                "Run this and restart:\n"
                "  pip install zxing-cpp"
            )
            return

        source = self.get_camera_source()
        if source is None:
            return

        self.result_label.config(text="Connecting to camera...")
        self.root.update()

        cap = cv2.VideoCapture(source)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not cap.isOpened():
            messagebox.showerror(
                "Camera Error",
                f"Could not open camera source:\n{source}\n\n"
                "Check camera index or RTSP URL."
            )
            self.result_label.config(text="")
            return

        self.result_label.config(
            text=f"Camera connected [{SCANNER_NAME}]. Hold barcode steady...\nPress 'q' to cancel."
        )
        self.root.update()

        output_shown = False

        while not output_shown:
            ret, frame = cap.read()
            if not ret:
                messagebox.showerror("Camera Error", "Failed to read frame. Stream disconnected.")
                break

            detected_data = None
            detected_rect = None

            for variant in self.get_preprocessed_variants(frame):
                results = decode_barcodes(variant)
                if results:
                    detected_data = results[0]["data"]
                    detected_rect = results[0]["rect"]
                    break

            if detected_data:
                print(f"[SCAN] Detected: {detected_data}")

                if detected_rect:
                    x, y, w, h = detected_rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                    cv2.putText(frame, detected_data, (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.imshow("Barcode Scanner", frame)
                cv2.waitKey(600)

                self.result_label.config(
                    text=f"Barcode: {detected_data}\nFetching from Google Books..."
                )
                self.root.update()

                book_info = self.fetch_book_info_from_api(detected_data)

                if book_info:
                    # ✅ FIX: Save to CSV after successful API fetch
                    saved = self.save_book_to_csv(detected_data, book_info)
                    save_status = "📁 Saved to library." if saved else "📁 Already in library (not duplicated)."

                    result_text = (
                        f"✅ Found: '{book_info['title']}'\n"
                        f"👤 Author(s): {book_info['authors']}\n"
                        f"🏷️ Category: {book_info['category']}\n"
                        f"🏢 Publisher: {book_info['publisher']} ({book_info['publishedDate']})\n"
                        f"📖 {book_info['description'][:200]}...\n"
                        f"{save_status}"
                    )
                    recs = self.fetch_recommendations_from_api(
                        book_info['category'], book_info['title']
                    )
                    if recs:
                        result_text += "\n\n📚 You might also like:"
                        for rec in recs:
                            result_text += f"\n  • {rec}"
                    else:
                        result_text += "\n\nNo recommendations found."
                else:
                    csv_title, csv_genre = self.get_book_info_from_csv(detected_data)
                    if csv_title:
                        result_text = f"✅ Found in local DB: '{csv_title}' (Genre: {csv_genre})"
                        recs = self.recommend_books_from_csv(csv_genre, csv_title)
                        if recs:
                            result_text += "\n\n📚 You might also like:"
                            for rec in recs:
                                result_text += f"\n  • {rec}"
                    else:
                        result_text = (
                            f"❌ Book not found for barcode: {detected_data}\n"
                            "Not in Google Books API or local database."
                        )

                self.result_label.config(text=result_text)
                output_shown = True
                break

            h_f, w_f = frame.shape[:2]
            cx, cy = w_f // 2, h_f // 2
            bw, bh = int(w_f * 0.6), int(h_f * 0.35)
            cv2.rectangle(
                frame,
                (cx - bw // 2, cy - bh // 2),
                (cx + bw // 2, cy + bh // 2),
                (0, 255, 255), 2
            )
            cv2.putText(frame,
                        "Hold barcode STEADY inside the box | Press 'q' to quit",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("Barcode Scanner", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.result_label.config(text="Scan cancelled.")
                break

        cap.release()
        cv2.destroyAllWindows()

    # -------------------------------------------------------------------------
    # CSV Methods
    # -------------------------------------------------------------------------

    def get_book_info_from_csv(self, barcode_data):
        if not os.path.exists(CSV_FILE):
            return None, None
        with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['barcode'] == barcode_data:
                    return row['title'], row['genre']
        return None, None

    def recommend_books_from_csv(self, genre, current_book_title):
        recommendations = []
        if not os.path.exists(CSV_FILE):
            return recommendations
        with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['genre'] == genre and row['title'] != current_book_title:
                    recommendations.append(row['title'])
                if len(recommendations) >= 3:
                    break
        return recommendations

    # -------------------------------------------------------------------------
    # UI Buttons
    # -------------------------------------------------------------------------

    def view_total_books(self):
        total_books = 0
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                total_books = sum(1 for row in reader)
        messagebox.showinfo("Total Books", f"Total number of books: {total_books}")

    def list_books(self):
        books = []
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                books = [row['title'] for row in reader]
        if books:
            messagebox.showinfo("List of Books", "Books:\n" + "\n".join(books))
        else:
            messagebox.showinfo("List of Books", "No books found.")

    def add_book(self):
        add_book_window = tk.Toplevel(self.root)
        add_book_window.title("Add Book")
        add_book_window.geometry("420x520")
        add_book_window.configure(bg="#f9f9f9")
        add_book_window.resizable(False, False)

        isbn_frame = tk.LabelFrame(
            add_book_window, text="  📖 Fetch by ISBN (Testing)  ",
            font=("Arial", 10, "bold"), bg="#f9f9f9", fg="#007bff",
            padx=10, pady=8
        )
        isbn_frame.pack(padx=15, pady=(15, 5), fill="x")

        tk.Label(isbn_frame, text="Enter ISBN:", bg="#f9f9f9",
                 font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=4)

        isbn_entry = tk.Entry(isbn_frame, width=22, font=("Arial", 11))
        isbn_entry.grid(row=0, column=1, padx=8, pady=4)
        isbn_entry.focus()

        status_label = tk.Label(isbn_frame, text="", bg="#f9f9f9",
                                font=("Arial", 9), fg="#555555", wraplength=360)
        status_label.grid(row=1, column=0, columnspan=2, pady=2, sticky="w")

        details_frame = tk.LabelFrame(
            add_book_window, text="  Book Details  ",
            font=("Arial", 10, "bold"), bg="#f9f9f9", fg="#333333",
            padx=10, pady=8
        )
        details_frame.pack(padx=15, pady=5, fill="x")

        fields = {}
        field_defs = [
            ("title",     "Title *"),
            ("barcode",   "Barcode/ISBN *"),
            ("genre",     "Genre *"),
            ("author",    "Author"),
            ("publisher", "Publisher"),
        ]

        for i, (key, label) in enumerate(field_defs):
            tk.Label(details_frame, text=f"{label}:", bg="#f9f9f9",
                     font=("Arial", 10)).grid(row=i, column=0, sticky="w", pady=3)
            entry = tk.Entry(details_frame, width=28, font=("Arial", 10))
            entry.grid(row=i, column=1, padx=8, pady=3)
            fields[key] = entry

        def fetch_by_isbn():
            isbn = isbn_entry.get().strip()
            if not isbn:
                status_label.config(text="⚠️ Please enter an ISBN number.", fg="orange")
                return

            status_label.config(text="🔍 Fetching from Google Books API...", fg="#007bff")
            add_book_window.update()

            book_info = self.fetch_book_info_from_api(isbn)

            if book_info:
                fields["title"].delete(0, tk.END)
                fields["title"].insert(0, book_info["title"])
                fields["barcode"].delete(0, tk.END)
                fields["barcode"].insert(0, isbn)
                fields["genre"].delete(0, tk.END)
                fields["genre"].insert(0, book_info["category"])
                fields["author"].delete(0, tk.END)
                fields["author"].insert(0, book_info["authors"])
                fields["publisher"].delete(0, tk.END)
                fields["publisher"].insert(0,
                    f"{book_info['publisher']} ({book_info['publishedDate']})")

                status_label.config(
                    text=f"✅ Book found: '{book_info['title']}' — review and click Add Book.",
                    fg="green"
                )
            else:
                status_label.config(
                    text=f"❌ No book found for ISBN '{isbn}'. Fill details manually.",
                    fg="red"
                )
                fields["barcode"].delete(0, tk.END)
                fields["barcode"].insert(0, isbn)

        fetch_btn = tk.Button(
            isbn_frame, text="🔍 Fetch Details", command=fetch_by_isbn,
            bg="#007bff", fg="white", font=("Arial", 10, "bold"),
            relief="flat", padx=10, pady=4, cursor="hand2"
        )
        fetch_btn.grid(row=0, column=2, padx=6, pady=4)

        isbn_entry.bind("<Return>", lambda e: fetch_by_isbn())

        def save_book():
            title     = fields["title"].get().strip()
            barcode   = fields["barcode"].get().strip()
            genre     = fields["genre"].get().strip()
            author    = fields["author"].get().strip()
            publisher = fields["publisher"].get().strip()

            if not title or not barcode or not genre:
                messagebox.showerror("Input Error",
                                     "Title, Barcode/ISBN and Genre are required (marked with *).")
                return

            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('barcode') == barcode:
                            if not messagebox.askyesno(
                                "Duplicate Found",
                                f"A book with barcode '{barcode}' already exists:\n'{row['title']}'\n\nAdd anyway?"
                            ):
                                return
                            break

            file_exists = os.path.exists(CSV_FILE)
            with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
                fieldnames = ['title', 'barcode', 'genre', 'author', 'publisher']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    'title':     title,
                    'barcode':   barcode,
                    'genre':     genre,
                    'author':    author,
                    'publisher': publisher,
                })

            messagebox.showinfo("Success", f"✅ '{title}' added successfully!")
            add_book_window.destroy()

        btn_frame = tk.Frame(add_book_window, bg="#f9f9f9")
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="✅ Add Book", command=save_book,
            bg="#28a745", fg="white", font=("Arial", 11, "bold"),
            relief="flat", padx=16, pady=6, cursor="hand2"
        ).grid(row=0, column=0, padx=8)

        tk.Button(
            btn_frame, text="✖ Cancel", command=add_book_window.destroy,
            bg="#dc3545", fg="white", font=("Arial", 11, "bold"),
            relief="flat", padx=16, pady=6, cursor="hand2"
        ).grid(row=0, column=1, padx=8)


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = LibraryManagementApp(root)

    root.style = ttk.Style()
    root.style.theme_use('clam')
    root.style.configure('Custom.TButton', background='#007bff', foreground='#ffffff',
                          font=('Arial', 12, 'bold'))

    root.mainloop()