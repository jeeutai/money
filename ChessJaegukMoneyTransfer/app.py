from flask import Flask, render_template, request, redirect, url_for, session, flash
import csv
import os
import uuid
from datetime import datetime
import qrcode
from PIL import Image
import io
import base64
from flask_share import Share
from flask_restful import Api, Resource
import logging
import time

app = Flask(__name__)
app.secret_key = 'chessmoney_secret_key'
api = Api(app)

# 파일 경로 설정
USERS_FILE = 'data/users.csv'
TRANSACTIONS_FILE = 'data/transactions.csv'
LOGIN_FILE = 'data/login.csv'

# 디렉토리 생성
os.makedirs('data', exist_ok=True)

# 파일이 없으면 생성
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['id', 'password', 'balance', 'role'])
        # 관리자 계정 추가 (아이디, 비밀번호, 잔액(무한), 역할)
        writer.writerow(['admin', 'admin123', 'infinite', 'admin'])

if not os.path.exists(TRANSACTIONS_FILE):
    with open(TRANSACTIONS_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['sender', 'receiver', 'amount', 'timestamp'])

def load_users():
    users = {}
    with open(USERS_FILE, 'r', newline='', encoding='utf-8') as file:  # encoding 추가
        reader = csv.DictReader(file)
        for row in reader:
            users[row['id']] = {
                'password': row['password'],
                'balance': row['balance'],
                'role': row['role']
            }
    return users

# 사용자 정보 저장
def save_users(users):
    with open(USERS_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['id', 'password', 'balance', 'role'])
        writer.writeheader()
        for user_id, user_data in users.items():
            writer.writerow({
                'id': user_id,
                'password': user_data['password'],
                'balance': user_data['balance'],
                'role': user_data['role']
            })

# 거래 기록 저장
def save_transaction(sender, receiver, amount):
    with open(TRANSACTIONS_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([sender, receiver, amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
def load_transactions(user_id=None):
    transactions = []
    with open(TRANSACTIONS_FILE, 'r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if user_id is None or row['sender'] == user_id or row['receiver'] == user_id:
                transactions.append(row)
    return transactions
def save_login(user_id):
    with open(LOGIN_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        
        users = load_users()
        if user_id in users:
            flash('이미 사용 중인 아이디입니다.')
            return redirect(url_for('register'))
        
        users[user_id] = {
            'password': password,
            'balance': '100',  # 초기 잔액 100 체스머니
            'role': 'user'
        }
        save_users(users)
        flash('회원가입이 완료되었습니다.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        
        users = load_users()
        if user_id in users and users[user_id]['password'] == password:
            session['user_id'] = user_id
            session['role'] = users[user_id]['role']

            # 로그인 기록 저장
            save_login(user_id)   
            return redirect(url_for('dashboard'))
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.')
    
    return render_template('login.html')

# 로그아웃
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('home'))

# 대시보드
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    users = load_users()
    user_data = users[session['user_id']]
    
    # QR 코드 생성
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(session['user_id'])
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    qr_code = base64.b64encode(img_io.getvalue()).decode('utf-8')
    
    return render_template('dashboard.html', 
                           balance=user_data['balance'], 
                           role=user_data['role'],
                           qr_code=qr_code)

# 비밀번호 변경
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        
        users = load_users()
        if users[session['user_id']]['password'] == current_password:
            users[session['user_id']]['password'] = new_password
            save_users(users)
            flash('비밀번호가 변경되었습니다.')
            return redirect(url_for('dashboard'))
        else:
            flash('현재 비밀번호가 올바르지 않습니다.')
    
    return render_template('change_password.html')

# 송금
@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        receiver = request.form['receiver']
        amount = request.form['amount']
        
        try:
            amount = int(amount)
            if amount <= 0:
                flash('송금액은 1 이상이어야 합니다.')
                return redirect(url_for('transfer'))
        except ValueError:
            flash('유효한 금액을 입력하세요.')
            return redirect(url_for('transfer'))
        
        users = load_users()
        sender = session['user_id']
        
        if receiver not in users:
            flash('받는 사람의 아이디가 존재하지 않습니다.')
            return redirect(url_for('transfer'))
        
        if sender == receiver:
            flash('자기 자신에게 송금할 수 없습니다.')
            return redirect(url_for('transfer'))
        
        if users[sender]['balance'] != 'infinite' and int(users[sender]['balance']) < amount:
            flash('잔액이 부족합니다.')
            return redirect(url_for('transfer'))
        
        # 송금 처리
        if users[sender]['balance'] != 'infinite':
            users[sender]['balance'] = str(int(users[sender]['balance']) - amount)
        
        users[receiver]['balance'] = str(int(users[receiver]['balance']) + amount)
        save_users(users)
        
        # 거래 기록 저장
        save_transaction(sender, receiver, amount)
        
        flash('송금이 완료되었습니다.')
        return redirect(url_for('dashboard'))
    
    return render_template('transfer.html')

# QR 코드 결제
@app.route('/qr_payment', methods=['GET', 'POST'])
def qr_payment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        receiver = request.form['receiver']
        amount = request.form['amount']
        
        try:
            amount = int(amount)
            if amount <= 0:
                flash('결제액은 1 이상이어야 합니다.')
                return redirect(url_for('qr_payment'))
        except ValueError:
            flash('유효한 금액을 입력하세요.')
            return redirect(url_for('qr_payment'))
        
        users = load_users()
        sender = session['user_id']
        
        if receiver not in users:
            flash('받는 사람의 아이디가 존재하지 않습니다.')
            return redirect(url_for('qr_payment'))
        
        if sender == receiver:
            flash('자기 자신에게 결제할 수 없습니다.')
            return redirect(url_for('qr_payment'))
        
        if users[sender]['balance'] != 'infinite' and int(users[sender]['balance']) < amount:
            flash('잔액이 부족합니다.')
            return redirect(url_for('qr_payment'))
        
        # 결제 처리
        if users[sender]['balance'] != 'infinite':
            users[sender]['balance'] = str(int(users[sender]['balance']) - amount)
        
        users[receiver]['balance'] = str(int(users[receiver]['balance']) + amount)
        save_users(users)
        
        # 거래 기록 저장
        save_transaction(sender, receiver, amount)
        
        flash('결제가 완료되었습니다.')
        return redirect(url_for('dashboard'))
    
    return render_template('qr_payment.html')

# QR 코드 스캔 결과 처리
@app.route('/qr_scan', methods=['POST'])
def qr_scan():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    qr_data = request.form['qr_data']
    
    users = load_users()
    if qr_data in users:
        return redirect(url_for('qr_payment') + f'?receiver={qr_data}')
    else:
        flash('유효하지 않은 QR 코드입니다.')
        return redirect(url_for('qr_payment'))

# 송금 내역 확인
@app.route('/transactions')
def transactions():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_transactions = load_transactions(user_id)
    
    return render_template('transactions.html', transactions=user_transactions)

# 관리자 페이지
@app.route('/admin')
def admin():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('dashboard'))
    
    users = load_users()
    return render_template('admin.html', users=users)

# 관리자: 회원 추가
@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        balance = request.form['balance']
        role = request.form['role']
        
        users = load_users()
        if user_id in users:
            flash('이미 사용 중인 아이디입니다.')
            return redirect(url_for('add_user'))
        
        users[user_id] = {
            'password': password,
            'balance': balance,
            'role': role
        }
        save_users(users)
        flash('회원이 추가되었습니다.')
        return redirect(url_for('admin'))
    
    return render_template('add_user.html')

# 관리자: 회원 삭제
@app.route('/admin/delete_user/<user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('dashboard'))
    
    if user_id == session['user_id']:
        flash('자기 자신을 삭제할 수 없습니다.')
        return redirect(url_for('admin'))
    
    users = load_users()
    if user_id in users:
        del users[user_id]
        save_users(users)
        flash('회원이 삭제되었습니다.')
    
    return redirect(url_for('admin'))

# 관리자: 회원 정보 수정
@app.route('/admin/edit_user/<user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('dashboard'))
    
    users = load_users()
    if user_id not in users:
        flash('존재하지 않는 회원입니다.')
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        password = request.form['password']
        balance = request.form['balance']
        role = request.form['role']
        
        users[user_id] = {
            'password': password,
            'balance': balance,
            'role': role
        }
        save_users(users)
        flash('회원 정보가 수정되었습니다.')
        return redirect(url_for('admin'))
    
    return render_template('edit_user.html', user_id=user_id, user_data=users[user_id])

# 관리자: 전체 송금 내역 조회
@app.route('/admin/all_transactions')
def all_transactions():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('dashboard'))
    
    all_trans = load_transactions()
    return render_template('all_transactions.html', transactions=all_trans)

if __name__ == '__main__':
    app.run(debug=True)