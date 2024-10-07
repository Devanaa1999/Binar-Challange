import gradio as gr
import pandas as pd
import sqlite3
import os
import re

# Paths for the CSV file and database
file_path = 'archive/new_kamusalay.csv'
db_path = 'archive/kamus_alay.db'
abusive_path = 'archive/abusive.csv'

def create_database():
    """Creates the database and kamus_alay table if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS kamus_alay (
            slang TEXT PRIMARY KEY,
            formal TEXT
        )
        ''')
        conn.commit()
    except Exception as e:
        print(f"Error creating database table: {e}")
    finally:
        conn.close()

def load_data_to_db(file_path):
    """Loads data from CSV file into the kamus_alay table."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_csv(file_path, header=None, names=["slang", "formal"], encoding='ISO-8859-1')
        df.to_sql('kamus_alay', conn, if_exists='replace', index=False)
        conn.commit()
        print("Data successfully loaded into the database.")
    except Exception as e:
        print(f"Error loading data to database: {e}")
        return False
    finally:
        conn.close()
    return True

def load_data():
    """Fetches slang dictionary from the kamus_alay table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT slang, formal FROM kamus_alay")
        kamus_alay_dict = dict(cursor.fetchall())
    except sqlite3.OperationalError as e:
        print(f"Error: {e}. Ensure the database table 'kamus_alay' exists and is properly populated.")
        return {}
    finally:
        conn.close()
    return kamus_alay_dict

def cleansing_text(sample_text):
    """Cleanses and converts text from slang to formal."""
    try:
        sample_text = sample_text.lower()
        sample_text = re.sub(r'\\n|\\t|\\r', '', sample_text)
        sample_text = re.sub(r'\d+', '', sample_text)
        sample_text = re.sub(r'\b(\w+)( \1)+\b', r'\1', sample_text)
        sample_text = re.sub(r'([!.,?;:])\1+', r'\1', sample_text)
        sample_text = re.sub(r'\s+', ' ', sample_text).strip()

        # Load slang dictionary
        kamus_alay_dict = load_data()
        if not kamus_alay_dict:
            return "Error: Slang dictionary could not be loaded from the database."

        for slang, formal in kamus_alay_dict.items():
            sample_text = re.sub(r'\b' + re.escape(slang) + r'\b', formal, sample_text)

        # Load abusive words and cleanse them
        if os.path.exists(abusive_path):
            abusive_words = pd.read_csv(abusive_path, header=None, names=["abusive"], encoding='ISO-8859-1')
            abusive_words = abusive_words['abusive'].tolist()
            for word in abusive_words:
                sample_text = re.sub(r'\b' + re.escape(word) + r'\b', '', sample_text)

        return sample_text
    except Exception as e:
        return f"Error during text cleansing: {str(e)}"

def process_text(input_text):
    return cleansing_text(input_text)

def process_file(file):
    kamus_alay_dict = load_data()
    if not kamus_alay_dict:
        return "Error: Slang dictionary could not be loaded from the database."

    try:
        df = pd.read_csv(file.name, encoding='ISO-8859-1')
        if df.empty:
            return "Error: The uploaded file is empty."
        
        text_column = df.columns[0]
        if text_column not in df.columns:
            return f"Error: Column '{text_column}' not found in the file."
        
        # Apply cleansing and save processed text
        df['processed_text'] = df[text_column].apply(lambda x: process_text(str(x)))
        
        output_file = "processed_output.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        return output_file
    except Exception as e:
        return f"Error processing file: {str(e)}"

def process_input(text, file):
    if text and file:
        return "Please provide either text or a file, not both."
    elif text:
        return process_text(text)
    elif file:
        return process_file(file)
    else:
        return "Please provide either text or a file."

# Define Gradio interfaces
text_interface = gr.Interface(
    fn=process_text,
    inputs=gr.Textbox(label="Enter text"),
    outputs=gr.Textbox(label="Processed text"),
    title="Slang to Formal Converter - Text Input",
    description="Enter text to convert slang words to formal words."
)

file_interface = gr.Interface(
    fn=process_file,
    inputs=gr.File(label="Upload CSV file"),
    outputs=gr.File(label="Processed file"),
    title="Slang to Formal Converter - File Input",
    description="Upload a CSV file to convert slang words to formal words."
)

# Initialize database and load CSV data
create_database()
if load_data_to_db(file_path):
    print("Launching Gradio interface...")
    # Launch Gradio interface with both options
    gr.TabbedInterface([text_interface, file_interface], ["Text Input", "File Input"]).launch()
else:
    print("Failed to load initial data. Gradio interface will not be launched.")
