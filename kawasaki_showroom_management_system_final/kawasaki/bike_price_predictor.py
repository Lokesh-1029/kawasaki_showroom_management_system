import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib
import os

class KawasakiPricePredictor:
    def __init__(self):
        self.model = None
        self.model_file = 'kawasaki_price_model.pkl'
        
    def create_training_data(self):
        """Create sample training data for Kawasaki bikes"""
        
        # Sample data: [bike_age_years, km_driven, number_of_owners, original_price, current_price]
        data = {
            'bike_age': [1, 2, 3, 1, 2, 4, 3, 5, 2, 1, 3, 4, 2, 5, 6, 1, 3, 2, 4, 3],
            'km_driven': [5000, 15000, 25000, 8000, 18000, 35000, 28000, 
                         45000, 12000, 3000, 22000, 40000, 10000, 50000, 
                         60000, 4000, 20000, 16000, 42000, 30000],
            'owners': [1, 1, 2, 1, 1, 2, 2, 3, 1, 1, 2, 2, 1, 3, 3, 1, 2, 1, 2, 2],
            'original_price': [350000, 450000, 550000, 400000, 500000, 650000,
                              580000, 700000, 480000, 380000, 520000, 680000,
                              490000, 750000, 800000, 420000, 560000, 460000,
                              720000, 600000],
            'current_price': [320000, 380000, 420000, 365000, 410000, 480000,
                             440000, 490000, 395000, 355000, 430000, 470000,
                             400000, 480000, 500000, 385000, 435000, 400000,
                             460000, 450000]
        }
        
        df = pd.DataFrame(data)
        
        # Features (X) and Target (y)
        X = df[['bike_age', 'km_driven', 'owners', 'original_price']]
        y = df['current_price']
        
        return X, y
    
    def train_model(self):
        """Train the ML model"""
        print("🔄 Training price prediction model...")
        
        X, y = self.create_training_data()
        
        # Split data for training and testing
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Create and train model
        self.model = LinearRegression()
        self.model.fit(X_train, y_train)
        
        # Test the model
        predictions = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, predictions)
        
        print(f"✅ Model trained successfully!")
        print(f"📊 Model accuracy (Mean Absolute Error): ₹{mae:.2f}")
        
        # Save the model
        joblib.dump(self.model, self.model_file)
        print(f"💾 Model saved as '{self.model_file}'")
        
        return self.model
    
    def load_model(self):
        """Load pre-trained model if exists"""
        if os.path.exists(self.model_file):
            self.model = joblib.load(self.model_file)
            print("✅ Model loaded successfully!")
            return True
        else:
            print("⚠️ No saved model found. Training new model...")
            self.train_model()
            return True
    
    def predict_price(self, bike_age, km_driven, owners, original_price):
        """Predict current resale price"""
        if self.model is None:
            self.load_model()
        
        # Create input array
        input_data = np.array([[bike_age, km_driven, owners, original_price]])
        
        # Make prediction
        predicted_price = self.model.predict(input_data)[0]
        
        # Apply depreciation factor for more realistic pricing
        depreciation = 0.85 ** bike_age  # 15% depreciation per year
        adjusted_price = predicted_price * depreciation
        
        return max(adjusted_price, original_price * 0.3)  # Minimum 30% of original
    
    def get_depreciation_chart(self, original_price):
        """Generate depreciation chart data"""
        years = list(range(1, 8))
        prices = []
        
        for year in years:
            # Assume average 10,000 km per year, 1 owner for first 3 years
            km = year * 10000
            owners = 1 if year <= 3 else 2 if year <= 5 else 3
            price = self.predict_price(year, km, owners, original_price)
            prices.append(round(price, 2))
        
        return years, prices


# Standalone test function
def test_predictor():
    print("\n" + "="*50)
    print("🏍️ KAWASAKI BIKE PRICE PREDICTOR")
    print("="*50)
    
    predictor = KawasakiPricePredictor()
    
    # Train or load model
    predictor.load_model()
    
    print("\n📋 Enter bike details to predict current price:")
    print("-"*40)
    
    try:
        bike_age = float(input("Bike age (years): "))
        km_driven = float(input("Kilometers driven: "))
        owners = int(input("Number of owners: "))
        original_price = float(input("Original price (₹): "))
        
        predicted = predictor.predict_price(bike_age, km_driven, owners, original_price)
        
        print("\n" + "="*50)
        print("🎯 PREDICTION RESULT")
        print("="*50)
        print(f"📌 Bike age: {bike_age} years")
        print(f"📌 Kilometers: {km_driven:,.0f} km")
        print(f"📌 Owners: {owners}")
        print(f"📌 Original price: ₹{original_price:,.2f}")
        print(f"\n💰 Estimated current resale value: ₹{predicted:,.2f}")
        
        depreciation_percent = ((original_price - predicted) / original_price) * 100
        print(f"📉 Total depreciation: {depreciation_percent:.1f}%")
        
        # Show depreciation chart data
        years, prices = predictor.get_depreciation_chart(original_price)
        print("\n📊 Depreciation trend:")
        for i in range(len(years)):
            bar_length = int(prices[i] / original_price * 30)
            bar = "█" * bar_length
            print(f"  Year {years[i]}: ₹{prices[i]:,.0f} {bar}")
            
    except ValueError:
        print("❌ Please enter valid numbers!")


if __name__ == "__main__":
    test_predictor()