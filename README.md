# Library Book Scanner System 📚

A desktop application designed for library management using barcode scanning and the Google Books API. This system allows users to scan book barcodes via a webcam or RTSP camera, automatically fetch book details (title, author, genre, etc.), and store them in a local database.

## ✨ Features
- **Barcode Scanning:** Supports both Webcam and RTSP camera streams.
- **Smart Detection:** Uses `zxing-cpp` (or `pyzbar` as a fallback) with image preprocessing for high-accuracy barcode detection.
- **Google Books Integration:** Automatically fetches book details using the scanned ISBN/barcode.
- **Local Database:** Saves all book information into a persistent `books.csv` file.
- **Manual Entry:** Add books manually or fetch details by entering an ISBN number.
- **Inventory Management:** Easily view the total number of books and list all entries in your library.
- **Recommendation System:** Suggests similar books based on the category/genre of the scanned book.

## 🛠️ Prerequisites
- **Python:** 3.12.0 or higher is recommended.
- **Operating System:** Windows (optimized for Windows with `zxing-cpp`).

## 🚀 Installation

1. **Clone or Download** this repository to your local machine.
2. **Install the required dependencies** using `pip`:

   ```bash
   pip install opencv-python numpy zxing-cpp pyzbar
   # Optional: dlib (may require git and cmake)
   pip install git+https://github.com/davisking/dlib.git
   ```

   *Note: `zxing-cpp` is highly recommended for Windows as it works without additional DLLs.*

## 📖 How to Run

Run the application using Python:

```bash
python main.py
```

## 🎮 Usage Guide

### 1. Scanning a Barcode
- Select your camera source (**Webcam** or **RTSP Camera**).
- Click **Scan Barcode**.
- A camera window will appear. Hold the book's barcode steady inside the yellow guide box.
- Once detected, the system will fetch details and save them to `books.csv` automatically.
- Press **'q'** in the camera window to cancel a scan.

### 2. Manual Book Entry
- Click **Add Book**.
- You can either:
  - Enter the **ISBN** and click **Fetch Details** to automatically fill the form.
  - Manually type in the Title, Barcode, Genre, Author, and Publisher.
- Click **Add Book** to save.

### 3. Viewing Library
- **View Total Books:** Shows a quick count of all books in your database.
- **List Books:** Displays a list of all book titles currently in your library.

## 📁 Project Structure
- `main.py`: The main application code (GUI and logic).
- `books.csv`: Local database file (auto-generated if missing).
- `requirements.txt`: List of Python dependencies.

## 📜 Database Format
The system stores data in `books.csv` with the following headers:
`title, barcode, genre, author, publisher`
