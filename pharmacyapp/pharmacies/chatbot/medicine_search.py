import logging
from django.db.models import Q
from pharmacies.models import Medicine

logger = logging.getLogger(__name__)


class MedicineSearchService:
    def __init__(self):
        self.genre_mapping = {
            'gan': [11],'liver': [11],'bảo vệ gan': [11],'giải độc gan': [11],'tăng cường gan': [11],'milk thistle': [11],'si-liver': [11],'dr. liver': [11],
            'bổ gan': [11],'men gan cao': [11],'giảm men gan': [11],'viêm gan': [11],'gan nhiễm mỡ': [11],'nóng gan': [11],'mẩn ngứa': [11],'vàng da': [11],
            'thuốc bổ gan': [11],'giải rượu': [11],'detox gan': [11],'hỗ trợ chức năng gan': [11],

            'thận': [6],'niệu': [6],'tiểu tiện': [6],'bổ thận': [6],'kidney': [6],'đái dầm': [6],'đái không tự chủ': [6],'đái nhiều': [6],'tiểu đêm': [6],
            'tiểu rắt': [6],'tiểu buốt': [6],'tiểu không hết': [6],'viêm đường tiết niệu': [6],'đường tiểu': [6],'sỏi thận': [6],'thận yếu': [6],
            'đau lưng mỏi gối': [6],'ù tai': [6],'mộng tinh': [6],'di tinh': [6],'lục vị': [6],
            
            'tim': [9],'tim mạch': [9],'huyết áp': [9],'cao huyết áp': [9],'tụt huyết áp': [9],'huyết áp không ổn định': [9],'cholesterol': [9],'mỡ máu': [9],
            'triglyceride': [9],'xơ vữa động mạch': [9],'thiếu máu cơ tim': [9],'đau tức ngực': [9],'khó thở': [9],'mệt mỏi': [9],
            
            'xương': [4],'khớp': [4],'xương khớp': [4],'đau khớp': [4],'viêm khớp': [4],'fastum': [4],'salonpas': [4],'vai gáy': [4],'thoái hóa cột sống': [4],
            'thoái hóa khớp': [4],'đau lưng': [4],'đau vai gáy': [4],'đau mỏi': [4],'đau cơ': [4],'gout': [4],'viêm gân': [4],'giãn cơ': [4],'chấn thương cơ': [4],
            'mỏi gối': [4],'đau đầu gối': [4],'viêm khớp dạng thấp': [4],'viêm đa khớp': [4],'đau thần kinh tọa': [4],'đau cột sống': [4],'thuốc bôi xương khớp': [4],'thuốc xoa bóp': [4],
            
            'đau bụng': [12],'tiêu hóa': [12],'rối loạn tiêu hóa': [12],'đầy hơi': [12],'chướng bụng': [12],'ợ nóng': [12],'buồn nôn': [12],'ợ chua': [12],'khó tiêu': [12],'dạ dày': [12],
            'viêm loét dạ dày': [12],'trào ngược': [12],'trào ngược dạ dày': [12],'viêm đại tràng': [12],'táo bón': [12],'bón': [12],'tiêu chảy': [12],'nhiễm giun': [12],'tẩy giun': [12],

            'ho': [3],'ho khan': [3],'ho có đờm': [3],'viêm họng': [3],'viêm amidan': [3],'đau họng': [3],'rát họng': [3],'sát khuẩn họng': [3],'viêm mũi': [3],'nghẹt mũi': [3],'sổ mũi': [3],
            'chảy nước mũi': [3],'mũi': [3],'viêm xoang': [3],'tai': [3],'viêm tai': [3],'ù tai': [3],'cảm': [3],'cảm cúm': [3],'cảm lạnh': [3],'ngạt mũi': [3],'xịt mũi': [3],'thuốc nhỏ mũi': [3],'xông mũi': [3],
            
            'mắt': [2],'nhỏ mắt': [2],'thuốc nhỏ mắt': [2],'giọt mắt': [2],'khô mắt': [2],'mỏi mắt': [2],'rát mắt': [2],'đỏ mắt': [2],
            'ngứa mắt': [2],'viêm kết mạc': [2],'viêm giác mạc': [2],'tăng tiết ghèn': [2],'giảm thị lực': [2],
            
            'giun': [5],'sán': [5],'tẩy giun': [5],'tẩy sán': [5],'nhiễm giun': [5],'nhiễm sán': [5],'kí sinh trùng': [5],'ký sinh trùng': [5], 'ấu trùng': [5],'trứng giun': [5],

            'đau bụng kinh': [1],'sinh sản': [1],'sức khỏe sinh sản': [1],'âm đạo': [1],'viêm âm đạo': [1],'nấm âm đạo': [1],'trùng roi': [1],'phụ khoa': [1],'kinh nguyệt': [1],
            'rối loạn kinh nguyệt': [1],'mãn kinh': [1],'tiền mãn kinh': [1],'ích mẫu': [1],'estrogen': [1],'khí hư': [1],'đặt âm đạo': [1],'thuốc đặt phụ khoa': [1],
            
            'đau đầu': [4, 12, 10], 'sốt': [3, 10],'paracetamol': [3, 4, 10],'acetaminophen': [3, 4, 10],'aspirin': [4, 9],'ibuprofen': [4, 3],'hạ sốt': [3, 10],'thuốc giảm đau': [4],
            'giảm đau': [4],'thuốc nhức đầu': [4],'thuốc đau đầu': [4],'nóng sốt': [3, 10],'nhức đầu': [4],'panadol': [3, 10],'efferalgan': [3, 10],
            
            'vitamin': [10],'khoáng chất': [10],'thiếu sắt': [10],'thiếu vitamin': [10],'canxi': [10],'calcium': [10],'sắt': [10],'iron': [10],'bổ sung': [10],'vitamin d3': [10],'vitamin k2': [10],
            'vitamin c': [10],'vitamin e': [10],'dha': [10],'omega 3': [10],'bổ sung canxi': [10],'bổ sung sắt': [10],'bổ sung dha': [10],
            'bổ sung vitamin': [10],'dinh dưỡng': [10],'trẻ chậm lớn': [10],'suy dinh dưỡng': [10],'tăng đề kháng': [10],'miễn dịch': [10]
        }
        
        self.excluded_words = {
            'thuốc', 'của', 'cho', 'với', 'và', 'là', 'có', 'tôi', 'bị', 'về',
            'trong', 'để', 'được', 'như', 'hay', 'hoặc', 'nào', 'gì', 'thế',
            'này', 'đó', 'một', 'các', 'những', 'chống', 'mạnh', 'tốt', 'giải','here', 'đường', 'sinh',
            'kháng', 'không', 'tồn', 'tại', 'strong', 'sắt',
            'thiếu', 'thụt', 'ướt', 'khô', 'cảm', 'ơn'
        }
    
    def search_exact_match(self, question):
        """Tìm kiếm thuốc theo exact match với tên"""
        words = question.split()
        significant_words = [word for word in words if len(word) > 3]
        exact_match_medicines = Medicine.objects.none()
        if significant_words:
            name_query = Q()
            for word in significant_words:
                name_query &= Q(name__icontains=word)
            exact_match_medicines = Medicine.objects.filter(name_query).select_related('medicineGenre', 'produce').prefetch_related('images')[:3]
        return exact_match_medicines
    
    def search_by_genre(self, question):
        """Tìm kiếm thuốc theo genre mapping"""
        question_lower = question.lower()
        matching_genres = set()
        matched_keywords = []
        for keyword, genres in self.genre_mapping.items():
            if keyword in question_lower:
                matching_genres.update(genres)
                matched_keywords.append(keyword)
        medicines = Medicine.objects.none()
        if matching_genres:
            medicines = Medicine.objects.filter(medicineGenre_id__in=matching_genres).select_related('medicineGenre', 'produce').prefetch_related('images')
            # Nếu có quá nhiều kết quả, lọc thêm bằng keyword
            if medicines.count() > 3:
                refined_query = Q()
                for keyword in matched_keywords:
                    refined_query |= (Q(name__icontains=keyword) | Q(benefit__icontains=keyword) | Q(use__icontains=keyword))
                refined_medicines = medicines.filter(refined_query)[:3]
                if refined_medicines.exists():
                    medicines = refined_medicines
                else:
                    medicines = medicines[:3]
            else:
                medicines = medicines[:5]
        return medicines
    
    def format_medicine_data(self, medicines):
        """Format thông tin thuốc thành context và medicine_list"""
        context = "THÔNG TIN THUỐC CÓ SẴN:\n\n"
        medicine_list = []
        
        for i, med in enumerate(medicines, 1):
            context += f"THUỐC {i}: {med.name}\n"
            context += f"- Loại: {med.medicineGenre.name}\n"
            context += f"- Giá: {med.price:,.0f} VND\n"
            context += f"- Công dụng: {med.benefit}\n"
            context += f"- Cách dùng: {med.use}\n"
            context += f"- Nhà sản xuất: {med.produce.name}\n\n"
            
            medicine_images = [img.imgMedicineUrl.url for img in med.images.all() if img.imgMedicineUrl]
            
            medicine_list.append({
                'id': med.id,
                'name': med.name,
                'genre': med.medicineGenre.name,
                'price': f"{med.price:,.0f} VND",
                'formatted_price': f"{med.price:,.0f} VND",
                'benefit': med.benefit,
                'use': med.use,
                'description': med.benefit,
                'format': med.medicineGenre.name,
                'producer': med.produce.name,
                'images': medicine_images
            })
        
        return context, medicine_list
    
    def get_medicine_context(self, question):
        """Main method để lấy thông tin thuốc từ database"""
        exact_match_medicines = self.search_exact_match(question)
        if exact_match_medicines.exists():
            return self.format_medicine_data(exact_match_medicines)
        genre_medicines = self.search_by_genre(question)  
        if genre_medicines.exists():
            return self.format_medicine_data(genre_medicines)
        return "Không tìm thấy thông tin thuốc.\n", []
