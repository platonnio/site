from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Конфигурация SQLite базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модель Бронирования
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    checkin = db.Column(db.Date, nullable=False)
    checkout = db.Column(db.Date, nullable=False)
    guests = db.Column(db.Integer, default=1)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Создаем таблицы при первом запуске
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    bookings = Booking.query.all()
    return jsonify([{
        'id': b.id,
        'checkin': b.checkin.isoformat(),
        'checkout': b.checkout.isoformat(),
        'name': b.name
    } for b in bookings])

@app.route('/api/book', methods=['POST'])
def create_booking():
    data = request.json
    
    try:
        # Обрезаем возможные дополнительные символы в дате
        checkin_str = data['checkin'].split('T')[0] if 'T' in data['checkin'] else data['checkin']
        checkout_str = data['checkout'].split('T')[0] if 'T' in data['checkout'] else data['checkout']
        
        checkin = datetime.strptime(checkin_str, '%Y-%m-%d').date()
        checkout = datetime.strptime(checkout_str, '%Y-%m-%d').date()
        
        # Проверка что дата выезда после даты заезда
        if checkout <= checkin:
            return jsonify({
                'success': False,
                'message': 'Дата выезда должна быть после даты заезда'
            }), 400
            
        # Проверка что даты не в прошлом
        today = datetime.now().date()
        if checkin < today or checkout < today:
            return jsonify({
                'success': False,
                'message': 'Нельзя бронировать прошедшие даты'
            }), 400

        # Проверка на пересечение с существующими бронированиями
        conflict = Booking.query.filter(
            (Booking.checkin <= checkout) & 
            (Booking.checkout >= checkin)
        ).first()
        
        if conflict:
            return jsonify({
                'success': False,
                'message': f'Даты заняты (забронировано {conflict.name})'
            }), 400

        # Создание новой записи
        booking = Booking(
            name=data['name'],
            email=data['email'],
            phone=data.get('phone', ''),
            checkin=checkin,
            checkout=checkout,
            guests=data.get('guests', 1),
            message=data.get('message', '')
        )
        
        db.session.add(booking)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Бронирование успешно создано!',
            'booking_id': booking.id
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'Неверный формат даты: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка сервера: {str(e)}'
        }), 500
if __name__ == '__main__':
    app.run(debug=True)