from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    trust_score = db.Column(db.Float, default=5.0)
    skillcoins_balance = db.Column(db.Float, default=10.0)  # Starting with 10 coins
    ipfs_profile_hash = db.Column(db.String(100), nullable=True)  # Store IPFS hash here
    
    skills = db.relationship('Skill', backref='user', lazy=True)
    transactions_given = db.relationship('Transaction', foreign_keys='Transaction.offerer_id', backref='offerer', lazy=True)
    transactions_received = db.relationship('Transaction', foreign_keys='Transaction.requester_id', backref='requester', lazy=True)

class Skill(db.Model):
    __tablename__ = 'skill'
    
    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_offered = db.Column(db.Boolean, default=True)
    availability = db.Column(db.String(100), default='anytime')
    ipfs_hash = db.Column(db.String(100), nullable=True)  # Store IPFS hash here

class Transaction(db.Model):
    __tablename__ = 'transaction'
    
    id = db.Column(db.Integer, primary_key=True)
    offerer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    amount_paid = db.Column(db.Float)
    transaction_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    status = db.Column(db.String(20), default='completed')  # pending, completed, cancelled
    ipfs_hash = db.Column(db.String(100), nullable=True)  # Store IPFS hash here

class TrustScore(db.Model):
    __tablename__ = 'trust_score'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Float, default=5.0)
    feedback = db.Column(db.Text, nullable=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
