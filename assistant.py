import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import time
import json

# Load environment variables
load_dotenv()

# Set up OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
base_url = "https://api.openai.com/v1"

# Define API endpoints
list_assistants_url = f"{base_url}/assistants"
create_thread_url = f"{base_url}/threads"
create_message_url = f"{base_url}/threads/{{thread_id}}/messages"
create_run_url = f"{base_url}/threads/{{thread_id}}/runs"
retrieve_run_url = f"{base_url}/threads/{{thread_id}}/runs/{{run_id}}"
list_messages_url = f"{base_url}/threads/{{thread_id}}/messages"

class Assistant:
    def __init__(self, id, name, description, model):
        self.id = id
        self.name = name
        self.description = description
        self.model = model

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Assistant Dashboard")
        self.root.geometry("800x600")

        self.assistants = []
        self.fetch_assistants()

        self.create_widgets()

    def fetch_assistants(self):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"  # Updated to v2
        }
        try:
            response = requests.get(list_assistants_url, headers=headers)
            response.raise_for_status()
            data = response.json()['data']
            self.assistants = [
                Assistant(
                    a['id'],
                    a['name'],
                    a.get('description', 'No description'),
                    a['model']
                )
                for a in data
            ]
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Failed to fetch assistants: {str(e)}")

    def create_widgets(self):
        # Create a frame for the assistant list
        list_frame = ttk.Frame(self.root)
        list_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Create a treeview to display the assistants
        columns = ('Name', 'Description', 'Model')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings')

        # Define headings
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        # Add data to the treeview
        for assistant in self.assistants:
            self.tree.insert('', tk.END, values=(assistant.name, assistant.description, assistant.model))

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create buttons for actions
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Query", command=self.open_query_window).pack(side=tk.LEFT, padx=5)

    def open_query_window(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an assistant to query.")
            return
        
        assistant_index = self.tree.index(selected[0])
        assistant = self.assistants[assistant_index]

        self.query_window = tk.Toplevel(self.root)
        self.query_window.title(f"Query {assistant.name}")
        self.query_window.geometry("400x200")

        ttk.Label(self.query_window, text="Ask your question:").pack(pady=5)
        self.query_entry = ttk.Entry(self.query_window, width=50)
        self.query_entry.pack(pady=5)

        ttk.Button(self.query_window, text="Send", command=lambda: self.query_assistant(assistant)).pack(pady=10)

    def query_assistant(self, assistant):
        user_query = self.query_entry.get()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"  # Updated to v2
        }
        
        try:
            # Step 1: Create a new thread
            thread_response = requests.post(create_thread_url, headers=headers)
            thread_response.raise_for_status()
            thread_id = thread_response.json()['id']

            # Step 2: Add a message to the thread
            message_url = create_message_url.format(thread_id=thread_id)
            message_data = {"role": "user", "content": user_query}
            message_response = requests.post(message_url, headers=headers, json=message_data)
            message_response.raise_for_status()

            # Step 3: Run the assistant
            run_url = create_run_url.format(thread_id=thread_id)
            run_data = {"assistant_id": assistant.id}
            run_response = requests.post(run_url, headers=headers, json=run_data)
            run_response.raise_for_status()
            run_id = run_response.json()['id']

            # Step 4: Periodically retrieve the run to check the status
            while True:
                run_status_url = retrieve_run_url.format(thread_id=thread_id, run_id=run_id)
                status_response = requests.get(run_status_url, headers=headers)
                status_response.raise_for_status()
                status = status_response.json()['status']
                
                if status == 'completed':
                    break
                elif status in ['failed', 'cancelled', 'expired']:
                    raise Exception(f"Run failed with status: {status}")
                
                time.sleep(1)

            # Step 5: Retrieve the assistant's response
            messages_url = list_messages_url.format(thread_id=thread_id)
            messages_response = requests.get(messages_url, headers=headers)
            messages_response.raise_for_status()
            messages = messages_response.json()['data']
            
            assistant_message = next((m for m in messages if m['role'] == 'assistant'), None)
            
            if assistant_message:
                answer = assistant_message['content'][0]['text']['value']
                messagebox.showinfo("Assistant Response", answer)
            else:
                messagebox.showwarning("No Response", "The assistant did not provide a response.")

        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if e.response is not None:
                error_data = e.response.json()
                if 'error' in error_data:
                    error_message = f"{error_data['error']['message']} (Type: {error_data['error']['type']})"
            messagebox.showerror("Error", f"An error occurred: {error_message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DashboardApp(root)
    root.mainloop()
