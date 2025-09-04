#!/usr/bin/env python
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacyapp.settings')
django.setup()

from pharmacies.chatbot.rag_service import RAGMedicineService

def test_rag():
    print("🧪 Testing RAG Medicine Service...")
    
    try:
        # Khởi tạo RAG service
        rag_service = RAGMedicineService()
        
        # Test cases
        test_queries = [
            "Tôi bị đau đầu",
            "Thuốc cho ho khan",
            "Có thuốc bổ gan không?",
            "Tôi bị mất ngủ do căng thẳng"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'='*50}")
            print(f"🔍 Test {i}: '{query}'")
            print(f"{'='*50}")
            
            try:
                # Gọi RAG pipeline
                result = rag_service.generate_rag_response(query)
                
                print(f"✅ Response Type: {result.get('type', 'unknown')}")
                print(f"📊 Medicines Count: {result.get('medicines_count', 0)}")
                
                if 'rag_info' in result:
                    print(f"🔍 Search Method: {result['rag_info']['search_method']}")
                    print(f"📈 Total Candidates: {result['rag_info']['total_candidates']}")
                    if result['rag_info']['similarity_scores']:
                        print(f"🎯 Similarity Scores: {result['rag_info']['similarity_scores']}")
                
                print(f"🤖 Bot Response (first 200 chars): {result['response'][:200]}...")
                
                if result.get('medicines'):
                    print(f"💊 Found Medicines:")
                    for med in result['medicines'][:2]:  # Show first 2
                        print(f"   - {med['name']} ({med['price']}) - Score: {med.get('similarity_score', 'N/A')}")
                
            except Exception as e:
                print(f"❌ Error in test {i}: {str(e)}")
                
    except Exception as e:
        print(f"❌ RAG Service initialization failed: {str(e)}")
        print("💡 Make sure all dependencies are installed:")
        print("   pip install sentence-transformers scikit-learn numpy")

if __name__ == "__main__":
    test_rag()
