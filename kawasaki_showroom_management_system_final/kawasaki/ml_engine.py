# ml_engine.py
class KawasakiML:
    def __init__(self):
        self.user_profiles = {}
        self.bike_embeddings = self._create_bike_embeddings()
        
    def _create_bike_embeddings(self):
        bikes_data = {
            'Ninja 400': {'cc': 399, 'type': 'sport', 'price': 550000, 'performance': 7},
            'Ninja 650': {'cc': 649, 'type': 'sport', 'price': 720000, 'performance': 8},
            'Z900': {'cc': 948, 'type': 'naked', 'price': 930000, 'performance': 9},
            'Ninja H2': {'cc': 998, 'type': 'superbike', 'price': 3500000, 'performance': 10},
            'Versys 650': {'cc': 649, 'type': 'touring', 'price': 750000, 'performance': 7.5},
            'Vulcan 900': {'cc': 903, 'type': 'cruiser', 'price': 880000, 'performance': 7},
            'J300': {'cc': 299, 'type': 'scooter', 'price': 450000, 'performance': 5},
            'J125': {'cc': 125, 'type': 'scooter', 'price': 250000, 'performance': 4}
        }
        return bikes_data
    
    def get_ai_recommendations(self, user_id, user_history=None):
        recommendations = ['Ninja 400', 'Z900', 'Versys 650', 'Ninja 650', 'Ninja H2']
        return recommendations[:4]
    
    def predict_user_interest(self, user_id, bike_name):
        bike_features = self.bike_embeddings.get(bike_name, {})
        base_score = bike_features.get('performance', 5) * 10
        return min(100, base_score)
    
    def find_similar_bikes(self, bike_name, all_bikes, top_n=3):
        return ['Ninja 650', 'Z900', 'Versys 650'][:top_n]
    
    def get_ai_chat_response(self, user_query):
        query_lower = user_query.lower()
        if 'price' in query_lower or 'cost' in query_lower:
            return "Our bikes range from ₹2.5 Lakhs for J125 to ₹35 Lakhs for Ninja H2. Which model interests you?"
        elif 'test ride' in query_lower:
            return "You can book a test ride from the Test Ride section! We offer free test rides for all models."
        elif 'best' in query_lower or 'top' in query_lower:
            return "The Ninja H2 is our flagship superbike. For daily use, Ninja 400 and Versys 650 are most popular!"
        elif 'finance' in query_lower or 'emi' in query_lower:
            return "We offer flexible financing options with EMIs starting from ₹9,999/month."
        else:
            return "Welcome to Kawasaki! Would you like to know about prices, test rides, or book a bike?"