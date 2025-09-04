import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from django.db.models import Q
from pharmacies.models import Medicine
from .openai_service import OpenAIService

logger = logging.getLogger(__name__)


class RAGMedicineService:
    """RAG-enhanced Medicine Search Service with vector embeddings"""
    
    def __init__(self):
        # Khởi tạo model embedding
        self.encoder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')  # Hỗ trợ tiếng Việt
        self.openai_service = OpenAIService()
        
        # Cache embeddings để tăng performance
        self._medicine_embeddings = None
        self._medicine_texts = None
        self._medicines_cache = None
        
    def _get_all_medicines(self):
        """Lấy tất cả thuốc từ database"""
        if self._medicines_cache is None:
            self._medicines_cache = Medicine.objects.filter(active=True).select_related('medicineGenre', 'produce').prefetch_related('images')
        return self._medicines_cache
    
    def _create_medicine_text(self, medicine):
        """Tạo text representation cho thuốc"""
        text_parts = [
            medicine.name,
            medicine.medicineGenre.name if medicine.medicineGenre else "",
            medicine.benefit or "",
            medicine.use or "",
            medicine.description or "",
            medicine.ingredient or "",
            medicine.produce.name if medicine.produce else ""
        ]
        return " ".join([part for part in text_parts if part]).strip()
    
    def _build_medicine_embeddings(self):
        """Tạo embeddings cho tất cả thuốc"""
        if self._medicine_embeddings is None:
            medicines = self._get_all_medicines()
            self._medicine_texts = [self._create_medicine_text(med) for med in medicines]
            self._medicine_embeddings = self.encoder.encode(self._medicine_texts)
            logger.info(f"Created embeddings for {len(self._medicine_texts)} medicines")
    
    def semantic_search(self, user_question, top_k=5, similarity_threshold=0.3):
        """Tìm kiếm thuốc bằng semantic similarity"""
        self._build_medicine_embeddings()
        
        # Encode câu hỏi người dùng
        question_embedding = self.encoder.encode([user_question])
        
        # Tính cosine similarity
        similarities = cosine_similarity(question_embedding, self._medicine_embeddings)[0]
        
        # Lấy top_k thuốc có similarity cao nhất
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Filter theo threshold
        relevant_medicines = []
        medicines = list(self._get_all_medicines())
        
        for idx in top_indices:
            if similarities[idx] >= similarity_threshold:
                medicine = medicines[idx]
                relevant_medicines.append({
                    'medicine': medicine,
                    'similarity_score': float(similarities[idx]),
                    'matched_text': self._medicine_texts[idx]
                })
        
        logger.info(f"Found {len(relevant_medicines)} relevant medicines for query: '{user_question}'")
        return relevant_medicines
    
    def hybrid_search(self, user_question):
        """Kết hợp exact match và semantic search"""
        # 1. Thử exact match trước
        exact_matches = self._exact_match_search(user_question)
        if exact_matches:
            return [{'medicine': med, 'similarity_score': 1.0, 'search_type': 'exact'} for med in exact_matches]
        
        # 2. Semantic search
        semantic_results = self.semantic_search(user_question, top_k=5, similarity_threshold=0.2)
        for result in semantic_results:
            result['search_type'] = 'semantic'
            
        return semantic_results
    
    def _exact_match_search(self, question):
        """Tìm kiếm exact match (fallback cho semantic search)"""
        words = question.split()
        significant_words = [word for word in words if len(word) > 3]
        
        if not significant_words:
            return []
            
        name_query = Q()
        for word in significant_words:
            name_query &= Q(name__icontains=word)
            
        return list(Medicine.objects.filter(name_query).select_related('medicineGenre', 'produce').prefetch_related('images')[:3])
    
    def format_rag_context(self, search_results):
        """Format kết quả RAG thành context cho OpenAI"""
        if not search_results:
            return "Không tìm thấy thông tin thuốc phù hợp.\n", []
        
        context = "THÔNG TIN THUỐC LIÊN QUAN (Tìm kiếm thông minh):\n\n"
        medicine_list = []
        
        for i, result in enumerate(search_results, 1):
            med = result['medicine']
            similarity = result.get('similarity_score', 0)
            search_type = result.get('search_type', 'unknown')
            
            context += f"THUỐC {i}: {med.name} (Độ liên quan: {similarity:.2f}, Loại tìm kiếm: {search_type})\n"
            context += f"- Loại: {med.medicineGenre.name if med.medicineGenre else 'N/A'}\n"
            context += f"- Giá: {med.price:,.0f} VND\n"
            context += f"- Công dụng: {med.benefit or 'N/A'}\n"
            context += f"- Cách dùng: {med.use or 'N/A'}\n"
            context += f"- Nhà sản xuất: {med.produce.name if med.produce else 'N/A'}\n\n"
            
            medicine_images = [img.imgMedicineUrl.url for img in med.images.all() if img.imgMedicineUrl]
            
            medicine_list.append({
                'id': med.id,
                'name': med.name,
                'genre': med.medicineGenre.name if med.medicineGenre else 'N/A',
                'price': f"{med.price:,.0f} VND",
                'formatted_price': f"{med.price:,.0f} VND",
                'benefit': med.benefit or 'N/A',
                'use': med.use or 'N/A',
                'description': med.benefit or 'N/A',
                'format': med.medicineGenre.name if med.medicineGenre else 'N/A',
                'producer': med.produce.name if med.produce else 'N/A',
                'images': medicine_images,
                'similarity_score': similarity,
                'search_type': search_type
            })
        
        return context, medicine_list
    
    def generate_rag_response(self, user_question):
        """Main method cho RAG pipeline"""
        try:
            # 1. Retrieval: Tìm kiếm thuốc liên quan
            search_results = self.hybrid_search(user_question)
            
            # 2. Augmentation: Format context
            context, medicine_list = self.format_rag_context(search_results)
            
            # 3. Generation: Tạo response với OpenAI
            if medicine_list:
                response_data = self.openai_service.generate_response(user_question, context, medicine_list)
                response_data['rag_info'] = {
                    'search_method': 'RAG (Retrieval-Augmented Generation)',
                    'total_candidates': len(search_results),
                    'similarity_scores': [r.get('similarity_score', 0) for r in search_results]
                }
            else:
                response_data = self.openai_service.generate_response(user_question, context, [])
                response_data['rag_info'] = {
                    'search_method': 'RAG (No relevant medicines found)',
                    'total_candidates': 0,
                    'similarity_scores': []
                }
            
            return response_data
            
        except Exception as e:
            logger.error(f"RAG pipeline error: {str(e)}")
            # Fallback to simple response
            return {
                'response': 'Xin lỗi, tôi đang gặp sự cố kỹ thuật. Vui lòng thử lại sau.',
                'medicines': [],
                'type': 'error',
                'medicines_count': 0,
                'rag_info': {
                    'search_method': 'Error fallback',
                    'error': str(e)
                }
            }
    
    def refresh_embeddings(self):
        """Làm mới embeddings khi có thuốc mới"""
        self._medicine_embeddings = None
        self._medicine_texts = None
        self._medicines_cache = None
        logger.info("Medicine embeddings cache cleared")
