from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import json
from collections import deque
import heapq

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database initialization
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE,
                 password TEXT,
                 name TEXT,
                 email TEXT)''')
    
    # Friendships table (graph edges)
    c.execute('''CREATE TABLE IF NOT EXISTS friendships
                 (user1_id INTEGER,
                 user2_id INTEGER,
                 PRIMARY KEY (user1_id, user2_id),
                 FOREIGN KEY (user1_id) REFERENCES users(id),
                 FOREIGN KEY (user2_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

init_db()

# Graph algorithms
class SocialGraph:
    def __init__(self):
        self.graph = {}
    
    def add_user(self, user_id):
        if user_id not in self.graph:
            self.graph[user_id] = []
    
    def add_friendship(self, user1, user2):
        self.add_user(user1)
        self.add_user(user2)
        if user2 not in self.graph[user1]:
            self.graph[user1].append(user2)
        if user1 not in self.graph[user2]:
            self.graph[user2].append(user1)
    
    def bfs(self, start):
        visited = set()
        queue = deque([start])
        visited.add(start)
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return result
    
    def dfs(self, start):
        visited = set()
        stack = [start]
        result = []
        
        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                result.append(node)
                for neighbor in reversed(self.graph.get(node, [])):
                    if neighbor not in visited:
                        stack.append(neighbor)
        return result
    
    def shortest_path(self, start, end):
        queue = deque()
        queue.append((start, [start]))
        visited = set()
        
        while queue:
            node, path = queue.popleft()
            if node == end:
                return path
            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None
    
    def dijkstra(self, start, end):
        # For unweighted graphs, Dijkstra's is equivalent to BFS
        return self.shortest_path(start, end)
    
    def suggest_friends(self, user_id, depth=2):
        suggestions = set()
        visited = set([user_id])
        queue = deque([(user_id, 0)])
        
        while queue:
            node, level = queue.popleft()
            if level > depth:
                continue
            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    if level == depth:
                        suggestions.add(neighbor)
                    queue.append((neighbor, level + 1))
        
        # Remove existing friends
        existing_friends = set(self.graph.get(user_id, []))
        return list(suggestions - existing_friends)
    
    def detect_communities(self):
        visited = set()
        communities = []
        
        for node in self.graph:
            if node not in visited:
                community = self.bfs(node)
                communities.append(community)
                visited.update(community)
        
        return communities

def build_social_graph():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    graph = SocialGraph()
    
    # Add all users
    c.execute("SELECT id FROM users")
    users = c.fetchall()
    for (user_id,) in users:
        graph.add_user(user_id)
    
    # Add all friendships
    c.execute("SELECT user1_id, user2_id FROM friendships")
    friendships = c.fetchall()
    for user1, user2 in friendships:
        graph.add_friendship(user1, user2)
    
    conn.close()
    return graph

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        email = request.form['email']
        
        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)",
                      (username, password, name, email))
            conn.commit()
            user_id = c.lastrowid
            conn.close()
            
            session['user_id'] = user_id
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Username already exists")
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    graph = build_social_graph()
    
    # Get user info
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name, username FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    
    # Get friends
    c.execute('''SELECT u.id, u.name 
                 FROM users u JOIN friendships f ON u.id = f.user2_id 
                 WHERE f.user1_id = ?''', (user_id,))
    friends = c.fetchall()
    conn.close()
    
    # Get friend suggestions
    suggestions = graph.suggest_friends(user_id)
    
    # Get suggested friend names
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    suggested_friends = []
    for friend_id in suggestions:
        c.execute("SELECT id, name FROM users WHERE id = ?", (friend_id,))
        suggested_friends.append(c.fetchone())
    conn.close()
    
    return render_template('dashboard.html', 
                         name=user[0], 
                         username=user[1],
                         friends=friends,
                         suggested_friends=suggested_friends)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name, username, email FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    
    return render_template('profile.html', 
                         name=user[0], 
                         username=user[1],
                         email=user[2])

@app.route('/friends')
def friends():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    graph = build_social_graph()
    
    # Get user info
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    
    # Get friends
    c.execute('''SELECT u.id, u.name 
                 FROM users u JOIN friendships f ON u.id = f.user2_id 
                 WHERE f.user1_id = ?''', (user_id,))
    friends = c.fetchall()
    
    # Get all users who are not friends
    c.execute('''SELECT id, name FROM users 
                 WHERE id != ? AND id NOT IN 
                 (SELECT user2_id FROM friendships WHERE user1_id = ?)''', 
              (user_id, user_id))
    non_friends = c.fetchall()
    conn.close()
    
    return render_template('friends.html', 
                         name=user[0],
                         friends=friends,
                         non_friends=non_friends)

@app.route('/add_friend/<int:friend_id>')
def add_friend(friend_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO friendships (user1_id, user2_id) VALUES (?, ?)", 
                 (user_id, friend_id))
        c.execute("INSERT INTO friendships (user1_id, user2_id) VALUES (?, ?)", 
                 (friend_id, user_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Friendship already exists
    conn.close()
    
    return redirect(url_for('friends'))

@app.route('/remove_friend/<int:friend_id>')
def remove_friend(friend_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM friendships WHERE user1_id = ? AND user2_id = ?", 
              (user_id, friend_id))
    c.execute("DELETE FROM friendships WHERE user1_id = ? AND user2_id = ?", 
              (friend_id, user_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('friends'))

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    graph = build_social_graph()
    
    # Get user info
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    
    # Get all users for path finding
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM users WHERE id != ?", (user_id,))
    other_users = c.fetchall()
    conn.close()
    
    # Get communities
    communities = graph.detect_communities()
    
    # Format communities with names
    formatted_communities = []
    for community in communities:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        placeholders = ','.join(['?']*len(community))
        c.execute(f"SELECT id, name FROM users WHERE id IN ({placeholders})", community)
        members = c.fetchall()
        conn.close()
        formatted_communities.append(members)
    
    return render_template('analytics.html',
                         name=user[0],
                         other_users=other_users,
                         communities=formatted_communities)

@app.route('/get_path/<int:target_id>')
def get_path(target_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'})
    
    user_id = session['user_id']
    graph = build_social_graph()
    
    path = graph.shortest_path(user_id, target_id)
    
    if not path:
        return jsonify({'error': 'No path found'})
    
    # Get names for the path
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    placeholders = ','.join(['?']*len(path))
    c.execute(f"SELECT id, name FROM users WHERE id IN ({placeholders})", path)
    path_with_names = c.fetchall()
    conn.close()
    
    return jsonify({
        'path': [{'id': user[0], 'name': user[1]} for user in path_with_names]
    })

if __name__ == '__main__':
    app.run(debug=True)