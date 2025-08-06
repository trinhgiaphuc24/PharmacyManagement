import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import InfoIcon from "@mui/icons-material/Info";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import axios, { endpoints } from "../utils/axiosConfig";

const Base = ({ children }) => {
  const navigate = useNavigate();
  const [showChat, setShowChat] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  // Khôi phục hoặc tạo mới session ID và messages
  useEffect(() => {
    // Khôi phục sessionId từ localStorage
    let savedSessionId = localStorage.getItem("chatbot_session_id");
    let savedMessages = localStorage.getItem("chatbot_messages");

    if (!savedSessionId) {
      // Tạo session ID mới nếu chưa có
      savedSessionId =
        "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
      localStorage.setItem("chatbot_session_id", savedSessionId);
    }

    setSessionId(savedSessionId);

    // Khôi phục messages từ localStorage
    if (savedMessages) {
      try {
        const parsedMessages = JSON.parse(savedMessages);
        setMessages(parsedMessages);
      } catch (error) {
        console.error("Lỗi khi khôi phục messages:", error);
        // Nếu lỗi, tạo message mặc định
        const defaultMessages = [
          {
            from: "bot",
            content:
              "Chào bạn! Tôi là chatbot tư vấn thuốc. Tôi có thể giúp gì cho bạn?",
          },
        ];
        setMessages(defaultMessages);
        localStorage.setItem(
          "chatbot_messages",
          JSON.stringify(defaultMessages)
        );
      }
    } else {
      // Nếu chưa có messages, tạo message mặc định
      const defaultMessages = [
        {
          from: "bot",
          content:
            "Chào bạn! Tôi là chatbot tư vấn thuốc. Tôi có thể giúp gì cho bạn?",
        },
      ];
      setMessages(defaultMessages);
      localStorage.setItem("chatbot_messages", JSON.stringify(defaultMessages));
    }
  }, []);

  // Auto scroll to bottom
  useEffect(() => {
    if (showChat && messagesEndRef.current) {
      // Đợi một chút để DOM render xong trước khi scroll
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  }, [messages, showChat]);

  // Scroll to bottom khi mở chat window
  useEffect(() => {
    if (showChat && messagesEndRef.current) {
      // Đợi DOM render và scroll xuống cuối
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "instant" });
      }, 200);
    }
  }, [showChat]);

  // Lưu messages vào localStorage mỗi khi có thay đổi
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem("chatbot_messages", JSON.stringify(messages));
    }
  }, [messages]);

  // Xóa lịch sử chat
  const clearChatHistory = () => {
    const defaultMessages = [
      {
        from: "bot",
        content:
          "Chào bạn! Tôi là chatbot tư vấn thuốc. Tôi có thể giúp gì cho bạn?",
      },
    ];
    setMessages(defaultMessages);
    localStorage.setItem("chatbot_messages", JSON.stringify(defaultMessages));

    // Tạo sessionId mới
    const newSessionId =
      "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
    setSessionId(newSessionId);
    localStorage.setItem("chatbot_session_id", newSessionId);
  };

  // Component hiển thị medicine card
  const MedicineCard = ({ medicine, setInput, setMessages, setLoading, loading, sendMessageToBot }) => {
    const handleViewDetail = () => {
      if (medicine.id) {
        // Đóng chat trước khi navigate
        setShowChat(false);
        // Navigate đến trang chi tiết thuốc
        navigate(`/medicines/${medicine.id}/`);
      }
    };

    const handleAddToCart = (e) => {
      e.stopPropagation(); // Prevent triggering the detail view
      // TODO: Implement add to cart functionality
      console.log("Add to cart:", medicine.name);
      // You can implement actual cart logic here
    };

    const handleAskAboutMedicine = (e) => {
      e.stopPropagation(); // Prevent triggering the detail view
      // Gán tên thuốc vào input và gửi tin nhắn
      const medicineQuestion = `Hãy tư vấn chi tiết về thuốc ${medicine.name}`;
      setInput(medicineQuestion);
      
      // Tự động gửi tin nhắn
      setTimeout(async () => {
        if (!loading) {
          // Thêm tin nhắn user
          setMessages((msgs) => [
            ...msgs,
            {
              from: "user",
              content: medicineQuestion,
              timestamp: new Date().toISOString(),
            },
          ]);

          // Thêm typing indicator
          setMessages((msgs) => [
            ...msgs,
            { from: "bot", content: "Đang trả lời...", isTyping: true },
          ]);

          setLoading(true);

          try {
            // Gửi tới chatbot API
            const botResponse = await sendMessageToBot(medicineQuestion);

            // Xóa typing indicator và thêm phản hồi thật
            setMessages((msgs) => [
              ...msgs.filter((msg) => !msg.isTyping),
              {
                from: "bot",
                content: botResponse,
                timestamp: new Date().toISOString(),
                isStructured: true,
              },
            ]);
          } catch (error) {
            // Xóa typing indicator và hiển thị lỗi
            setMessages((msgs) => [
              ...msgs.filter((msg) => !msg.isTyping),
              {
                from: "bot",
                content:
                  "Xin lỗi, tôi gặp sự cố khi xử lý câu hỏi của bạn. Vui lòng thử lại.",
                timestamp: new Date().toISOString(),
              },
            ]);
          } finally {
            setLoading(false);
            setInput(""); // Clear input sau khi gửi
          }
        }
      }, 100);
    };

    return (
      <div className="bg-gradient-to-r from-green-50 to-green-100 border border-green-200 rounded-xl p-4 mb-3 shadow-sm hover:shadow-md transition-all duration-200">
        <div className="flex items-start gap-3">
          {/* Ảnh thuốc */}
          <div className="flex-shrink-0">
            {medicine.images && medicine.images.length > 0 ? (
              <img
                src={medicine.images[0]}
                alt={medicine.name}
                className="w-20 h-20 object-cover rounded-lg border border-green-300 bg-white cursor-pointer hover:scale-105 transition-transform"
                onError={(e) => {
                  e.target.src = "https://via.placeholder.com/80x80?text=";
                }}
                onClick={handleViewDetail}
                title="Click để xem chi tiết"
              />
            ) : (
              <div
                className="w-20 h-20 bg-green-200 rounded-lg flex items-center justify-center text-3xl cursor-pointer hover:scale-105 transition-transform"
                onClick={handleViewDetail}
              >            
              </div>
            )}
          </div>

          {/* Thông tin thuốc */}
          <div className="flex-1 min-w-0">
            <h4
              className="font-semibold text-green-800 text-sm mb-2 line-clamp-2 hover:text-green-600 cursor-pointer"
              onClick={handleViewDetail}
            >
              {medicine.name}
            </h4>
            <p className="text-xs text-gray-600 mb-3 line-clamp-3">
              {medicine.description}
            </p>

            {/* Giá và dạng thuốc */}
            <div className="flex items-center justify-between mb-3">
              <span className="text-green-700 font-bold text-base">
                {medicine.formatted_price}
              </span>
              <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded-full border">
                {medicine.format}
              </span>
            </div>

            {/* Nhà sản xuất */}
            <p className="text-xs text-gray-500 mb-3">
              <span className="font-medium">NSX:</span> {medicine.producer}
            </p>

            {/* Buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleViewDetail}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white text-xs font-medium py-2 px-2 rounded-lg transition-all duration-200 flex items-center justify-center gap-1 hover:shadow-md"
                title="Xem thông tin chi tiết thuốc"
              >
                <InfoIcon fontSize="small" />
                <span>Chi tiết</span>
              </button>

              <button
                onClick={handleAskAboutMedicine}
                className="flex-1 bg-yellow-600 hover:bg-yellow-700 text-white text-xs font-medium py-2 px-2 rounded-lg transition-all duration-200 flex items-center justify-center gap-1 hover:shadow-md"
                title="Hỏi chatbot về thuốc này"
              >
                <SmartToyIcon fontSize="small" />
                <span>Hỏi đáp</span>
              </button>

              <button
                onClick={handleAddToCart}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium py-2 px-2 rounded-lg transition-all duration-200 flex items-center justify-center gap-1 hover:shadow-md"
                title="Thêm vào giỏ hàng"
              >
                <ShoppingCartIcon fontSize="small" />
                <span>Giỏ hàng</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Component parse và hiển thị structured response từ OpenAI
  const parseStructuredResponse = (text) => {
    console.log("=== PARSE STRUCTURED RESPONSE DEBUG ===");
    console.log("Input text:", text);
    console.log("Contains **:", text.includes('**'));
    
    const sections = {};
    
    // Thử regex cho format **header:** trước với nhiều pattern khác nhau
    const sectionPatterns = [
      /\*\*(.*?):\*\*([\s\S]*?)(?=\*\*.*?:\*\*|$)/g,  // **Header:** pattern
      /\*\*(.*?)\*\*:?\s*([\s\S]*?)(?=\*\*.*?\*\*|$)/g,  // **Header** pattern với optional :
      /(Giới thiệu và công dụng|Cách sử dụng|Giá cả|Lưu ý quan trọng):?\s*([\s\S]*?)(?=(Giới thiệu và công dụng|Cách sử dụng|Giá cả|Lưu ý quan trọng)|$)/gi  // Direct section names
    ];
    
    let matchCount = 0;
    
    for (let pattern of sectionPatterns) {
      let match;
      pattern.lastIndex = 0; // Reset regex
      
      while ((match = pattern.exec(text)) !== null) {
        const title = match[1].trim();
        const content = match[2].trim();
        
        // Normalize section names
        let normalizedTitle = title;
        if (title.toLowerCase().includes('giới thiệu') || title.toLowerCase().includes('công dụng')) {
          normalizedTitle = 'Giới thiệu và công dụng';
        } else if (title.toLowerCase().includes('cách') && (title.toLowerCase().includes('dùng') || title.toLowerCase().includes('sử dụng'))) {
          normalizedTitle = 'Cách sử dụng';
        } else if (title.toLowerCase().includes('giá')) {
          normalizedTitle = 'Giá cả';
        } else if (title.toLowerCase().includes('lưu ý') || title.toLowerCase().includes('cảnh báo')) {
          normalizedTitle = 'Lưu ý quan trọng';
        }
        
        if (content && content.length > 5) { // Only accept meaningful content
          sections[normalizedTitle] = content;
          matchCount++;
          console.log(`Match ${matchCount}:`, {title: normalizedTitle, content: content.substring(0, 100) + '...'});
        }
      }
      
      if (matchCount > 0) break; // If we found matches with this pattern, stop trying others
    }
    
    console.log("Total matches found with structured format:", matchCount);
    
    // Nếu không tìm thấy structured format, thử fallback parsing dựa trên keywords
    if (matchCount === 0) {
      console.log("No structured sections found, trying keyword-based parsing...");
      return parseByKeywords(text);
    }
    
    // Post-process để đảm bảo price information được phân loại đúng
    for (let [sectionName, content] of Object.entries(sections)) {
      if (sectionName !== 'Giá cả') {
        // Tìm thông tin giá trong các section khác và chuyển sang section Giá cả
        const priceRegex = /\d+[.,]\d+\s*VND|\d+\s*VND|\d+[.,]\d+\s*đồng/gi;
        const priceMatches = content.match(priceRegex);
        
        if (priceMatches && priceMatches.length > 0) {
          // Move price to correct section
          if (!sections['Giá cả']) {
            sections['Giá cả'] = priceMatches.join(', ');
          } else {
            sections['Giá cả'] += ', ' + priceMatches.join(', ');
          }
          
          // Remove price from current section
          sections[sectionName] = content.replace(priceRegex, '').replace(/giá\s*cả\s*:?\s*/gi, '').trim();
          console.log(`Moved price info from ${sectionName} to Giá cả:`, priceMatches);
        }
      }
    }
    
    console.log("Final sections after price processing:", sections);
    console.log("=== END DEBUG ===");
    
    return sections;
  };

  // Fallback: Parse text dựa trên keywords thay vì **Section:**
  const parseByKeywords = (text) => {
    console.log("=== KEYWORD PARSING START ===");
    console.log("Input text:", text);
    
    // Khởi tạo 4 section bắt buộc
    const sections = {
      'Giới thiệu và công dụng': '',
      'Cách sử dụng': '',
      'Giá cả': '',
      'Lưu ý quan trọng': ''
    };
    
    // BƯỚC 1: Tách riêng thông tin giá trước (priority cao nhất)
    const priceRegex = /\d+[.,]\d+\s*VND|\d+\s*VND|\d+[.,]\d+\s*đồng/gi;
    const priceMatches = text.match(priceRegex);
    
    if (priceMatches && priceMatches.length > 0) {
      sections['Giá cả'] = priceMatches.join(', ');
      console.log("Found price info:", sections['Giá cả']);
      
      // Loại bỏ thông tin giá khỏi text để tránh bị classify nhầm
      text = text.replace(priceRegex, '').replace(/giá\s*cả\s*:?\s*/gi, '').trim();
    }
    
    // Cố gắng tách text thành các phần dựa trên structure
    const paragraphs = text.split('\n').filter(line => line.trim()).map(line => line.trim());
    console.log("Total paragraphs after price extraction:", paragraphs.length);
    
    // Nếu có ít nhất 3 đoạn còn lại, chia cho 3 sections còn lại
    if (paragraphs.length >= 3) {
      const sectionNames = ['Giới thiệu và công dụng', 'Cách sử dụng', 'Lưu ý quan trọng'];
      const paragraphsPerSection = Math.ceil(paragraphs.length / 3);
      
      for (let i = 0; i < 3; i++) {
        const startIdx = i * paragraphsPerSection;
        const endIdx = Math.min((i + 1) * paragraphsPerSection, paragraphs.length);
        const sectionContent = paragraphs.slice(startIdx, endIdx).join(' ').trim();
        
        if (sectionContent) {
          sections[sectionNames[i]] = sectionContent;
          console.log(`Auto-assigned section ${i + 1}: ${sectionNames[i]} -> ${sectionContent.substring(0, 50)}...`);
        }
      }
    } else {
      // Nếu ít hơn 3 đoạn, sử dụng keyword matching với priority cao
      let usedParagraphs = new Set();
      
      // Keywords với độ ưu tiên cao
      const priorityKeywords = {
        'Lưu ý quan trọng': ['lưu ý', 'cảnh báo', 'tránh', 'không nên', 'chống chỉ định', 'thận trọng', 'tác dụng phụ', 'khuyên'],
        'Cách sử dụng': ['cách dùng', 'cách sử dụng', 'liều dùng', 'uống', 'nhỏ mắt', 'lần', 'ngày', 'sử dụng'],
        'Giới thiệu và công dụng': ['giới thiệu', 'là thuốc', 'là một', 'được sử dụng', 'công dụng', 'tác dụng', 'điều trị', 'chữa trị', 'hỗ trợ']
      };
      
      // Gán paragraph cho từng section theo priority
      for (let [sectionName, keywords] of Object.entries(priorityKeywords)) {
        for (let i = 0; i < paragraphs.length; i++) {
          if (usedParagraphs.has(i)) continue;
          
          const paragraph = paragraphs[i];
          let score = 0;
          
          for (let keyword of keywords) {
            if (paragraph.toLowerCase().includes(keyword.toLowerCase())) {
              score += keyword.length;
            }
          }
          
          // Nếu score đủ cao hoặc chứa keyword quan trọng
          if (score > 3 || keywords.some(k => paragraph.toLowerCase().includes(k.toLowerCase()) && k.length >= 5)) {
            if (!sections[sectionName]) {
              sections[sectionName] = paragraph;
              usedParagraphs.add(i);
              console.log(`Priority matched: ${sectionName} -> ${paragraph.substring(0, 50)}...`);
              break;
            }
          }
        }
      }
      
      // Gán các paragraph còn lại vào section chưa có content
      for (let i = 0; i < paragraphs.length; i++) {
        if (usedParagraphs.has(i)) continue;
        
        const paragraph = paragraphs[i];
        
        // Tìm section chưa có content
        for (let sectionName of ['Giới thiệu và công dụng', 'Cách sử dụng', 'Lưu ý quan trọng']) {
          if (!sections[sectionName]) {
            sections[sectionName] = paragraph;
            usedParagraphs.add(i);
            console.log(`Fallback assigned: ${sectionName} -> ${paragraph.substring(0, 50)}...`);
            break;
          }
        }
      }
    }
    
    // Đảm bảo mọi section đều có nội dung (fallback cuối cùng)
    const allText = text.replace(/\*\*/g, '').trim();
    
    if (!sections['Giới thiệu và công dụng']) {
      const sentences = allText.split('.').filter(s => s.trim());
      sections['Giới thiệu và công dụng'] = sentences.slice(0, 2).join('.').trim() + '.' || 'Thông tin về thuốc này.';
    }
    
    if (!sections['Cách sử dụng']) {
      const usageSentences = allText.split('.').filter(s => {
        const lower = s.toLowerCase();
        return lower.includes('dùng') || lower.includes('uống') || lower.includes('liều') || lower.includes('lần');
      });
      sections['Cách sử dụng'] = usageSentences[0]?.trim() + '.' || 'Sử dụng theo chỉ dẫn của bác sĩ.';
    }
    
    if (!sections['Giá cả']) {
      sections['Giá cả'] = 'Vui lòng liên hệ để biết giá cụ thể.';
    }
    
    if (!sections['Lưu ý quan trọng']) {
      sections['Lưu ý quan trọng'] = 'Tham khảo ý kiến dược sĩ trước khi sử dụng. Đọc kỹ hướng dẫn sử dụng.';
    }
    
    console.log("Final parsed sections:", sections);
    console.log("=== KEYWORD PARSING END ===");
    
    return sections;
  };

  // Component hiển thị structured response
  const StructuredMessage = ({ data }) => {
    // DEBUG: Log để xem data thực sự chứa gì
    console.log("=== STRUCTURED MESSAGE DEBUG ===");
    console.log("Full data object:", data);
    console.log("data.response_type:", data.response_type);
    console.log("data.message type:", typeof data.message);
    console.log("data.message content:", data.message);
    console.log("Message includes **:", data.message && data.message.includes('**'));
    console.log("=== END STRUCTURED MESSAGE DEBUG ===");
    
    if (!data.response_type || data.response_type === "unknown") {
      return (
        <div className="text-gray-800">{data.message || data.content}</div>
      );
    }

    // Nếu có response từ OpenAI, luôn cố gắng parse thành sections
    if (data.message && typeof data.message === 'string') {
      console.log("=== PARSING STRUCTURED RESPONSE ===");
      const sections = parseStructuredResponse(data.message);
      console.log("Parsed sections result:", sections);
      console.log("Number of sections:", Object.keys(sections).length);
      
      // Luôn hiển thị dạng sections - đảm bảo có đầy đủ 4 phần
      const sectionOrder = [
        'Giới thiệu và công dụng',
        'Cách sử dụng', 
        'Giá cả',
        'Lưu ý quan trọng'
      ];
      
      // Đảm bảo tất cả sections đều có content
      sectionOrder.forEach(sectionName => {
        if (!sections[sectionName] || sections[sectionName].trim() === '') {
          switch(sectionName) {
            case 'Giới thiệu và công dụng':
              sections[sectionName] = 'Thuốc này có tác dụng hỗ trợ điều trị và cải thiện sức khỏe.';
              break;
            case 'Cách sử dụng':
              sections[sectionName] = 'Sử dụng theo hướng dẫn của bác sĩ hoặc dược sĩ.';
              break;
            case 'Giá cả':
              sections[sectionName] = 'Vui lòng liên hệ nhà thuốc để biết giá chính xác.';
              break;
            case 'Lưu ý quan trọng':
              sections[sectionName] = 'Tham khảo ý kiến dược sĩ trước khi sử dụng. Đọc kỹ hướng dẫn sử dụng.';
              break;
          }
        }
      });
      
      return (
        <div className="space-y-4">
          {/* Render sections theo thứ tự cố định */}
          {sectionOrder.map((sectionName) => {
            const content = sections[sectionName];
            
            // Define colors for different section types
            let sectionStyle = "bg-gradient-to-r from-gray-50 to-gray-100 border-l-4 border-gray-400";
            let textColor = "text-gray-700";
            let headerColor = "text-gray-800";
            let icon = "📋";
            
            if (sectionName.includes('Giới thiệu')) {
              sectionStyle = "bg-gradient-to-r from-blue-50 to-blue-100 border-l-4 border-blue-400";
              textColor = "text-blue-700";
              headerColor = "text-blue-800";
              icon = "💊";
            } else if (sectionName.includes('Cách sử dụng')) {
              sectionStyle = "bg-gradient-to-r from-purple-50 to-purple-100 border-l-4 border-purple-400";
              textColor = "text-purple-700";
              headerColor = "text-purple-800";
              icon = "📖";
            } else if (sectionName.includes('Giá')) {
              sectionStyle = "bg-gradient-to-r from-orange-50 to-orange-100 border-l-4 border-orange-400";
              textColor = "text-orange-700";
              headerColor = "text-orange-800";
              icon = "💰";
            } else if (sectionName.includes('Lưu ý')) {
              sectionStyle = "bg-gradient-to-r from-red-50 to-red-100 border-l-4 border-red-400";
              textColor = "text-red-700";
              headerColor = "text-red-800";
              icon = "⚠️";
            }
            
            return (
              <div key={sectionName} className={`${sectionStyle} p-3 rounded-lg`}>
                <h4 className={`${headerColor} font-semibold text-sm mb-2 flex items-center`}>
                  <span className="mr-2">{icon}</span>
                  {sectionName}
                </h4>
                <p className={`${textColor} text-sm whitespace-pre-wrap`}>{content}</p>
              </div>
            );
          })}

          {/* Medicines - Hiển thị thuốc được đề xuất */}
          {data.medicines &&
            data.medicines.length > 0 &&
            data.response_type !== "text_only" && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <h4 className="text-green-700 font-semibold text-sm flex items-center">
                    <span className="mr-2">🏥</span>
                    Thuốc được đề xuất
                  </h4>
                  <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full font-medium">
                    {data.medicines.length} thuốc
                  </span>
                </div>
                <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
                  {data.medicines.map((medicine, index) => (
                    <MedicineCard
                      key={medicine.id || index}
                      medicine={medicine}
                      setInput={setInput}
                      setMessages={setMessages}
                      setLoading={setLoading}
                      loading={loading}
                      sendMessageToBot={sendMessageToBot}
                    />
                  ))}
                </div>
              </div>
            )}
        </div>
      );
    }

    // Fallback cho message thông thường
    return (
      <div className="space-y-4">
        {/* Header */}
        {data.header && (
          <div className="bg-gradient-to-r from-blue-50 to-blue-100 border-l-4 border-blue-400 p-3 rounded-lg">
            <p className="text-blue-800 font-medium text-sm flex items-start">
              <span className="mr-2">🔍</span>
              <span>{data.header}</span>
            </p>
          </div>
        )}

        {/* Message */}
        {data.message && (
          <div className="bg-gray-50 p-3 rounded-lg border">
            <p className="text-gray-800 text-sm">{data.message}</p>
          </div>
        )}

        {/* Medicines */}
        {data.medicines &&
          data.medicines.length > 0 &&
          data.response_type !== "text_only" && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <h4 className="text-green-700 font-semibold text-sm flex items-center">
                  <span className="mr-2">🏥</span>
                  Thuốc được đề xuất
                </h4>
                <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full font-medium">
                  {data.medicines.length} thuốc
                </span>
              </div>
              <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
                {data.medicines.map((medicine, index) => (
                  <MedicineCard
                    key={medicine.id || index}
                    medicine={medicine}
                    setInput={setInput}
                    setMessages={setMessages}
                    setLoading={setLoading}
                    loading={loading}
                    sendMessageToBot={sendMessageToBot}
                  />
                ))}
              </div>
            </div>
          )}

        {/* Specific Advice */}
        {data.specific_advice && data.specific_advice.length > 0 && (
          <div className="bg-gradient-to-r from-yellow-50 to-yellow-100 border border-yellow-200 rounded-lg p-3">
            <h4 className="text-yellow-800 font-semibold text-sm mb-2 flex items-center">
              📋 Lời khuyên cho {data.advice_type || "triệu chứng"}
            </h4>
            <ul className="space-y-1">
              {data.specific_advice.map((advice, index) => (
                <li
                  key={index}
                  className="text-yellow-700 text-sm flex items-start"
                >
                  <span className="text-yellow-500 mr-2 font-bold">•</span>
                  <span>{advice}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  // Gửi tin nhắn tới chatbot API
  const sendMessageToBot = async (userMessage) => {
    try {
      const response = await axios.post(endpoints.chatbot, {
        message: userMessage,
        session_id: sessionId,
      });

      console.log("API Response:", response.data); // Debug log

      // Trả về toàn bộ response data để component có thể render structured
      return response.data;
    } catch (error) {
      console.error("Lỗi chatbot:", error);
      if (error.response?.status === 500) {
        return {
          response_type: "error",
          message:
            "Xin lỗi, hệ thống tư vấn đang gặp sự cố. Vui lòng thử lại sau ít phút.",
        };
      }
      return {
        response_type: "error",
        message:
          "Xin lỗi, tôi không thể kết nối được. Vui lòng kiểm tra kết nối internet và thử lại.",
      };
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setLoading(true);

    // Thêm tin nhắn user
    setMessages((msgs) => [
      ...msgs,
      {
        from: "user",
        content: userMessage,
        timestamp: new Date().toISOString(),
      },
    ]);

    // Thêm typing indicator
    setMessages((msgs) => [
      ...msgs,
      { from: "bot", content: "Đang trả lời...", isTyping: true },
    ]);

    try {
      // Gửi tới chatbot API
      const botResponse = await sendMessageToBot(userMessage);

      // Xóa typing indicator và thêm phản hồi thật
      setMessages((msgs) => [
        ...msgs.filter((msg) => !msg.isTyping),
        {
          from: "bot",
          content: botResponse,
          timestamp: new Date().toISOString(),
          isStructured: true,
        },
      ]);
    } catch (error) {
      // Xóa typing indicator và hiển thị lỗi
      setMessages((msgs) => [
        ...msgs.filter((msg) => !msg.isTyping),
        {
          from: "bot",
          content:
            "Xin lỗi, tôi gặp sự cố khi xử lý câu hỏi của bạn. Vui lòng thử lại.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    if (!timestamp) return "";
    const date = new Date(timestamp);
    return date.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <>
      {children}

      {/* Nút lên đầu trang */}
      <button
        onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
        className="fixed bottom-6 right-6 bg-green-700 hover:bg-white hover:text-green-700 text-white p-3 rounded-full shadow-lg z-50 border hover:border-green-700 transition-all duration-300 hover:scale-110"
        title="Lên đầu trang"
      >
        <KeyboardArrowUpIcon fontSize="medium" />
      </button>

      {/* Nút chatbot */}
      <button
        className="fixed bottom-20 right-6 bg-green-700 hover:bg-white hover:text-green-700 text-white p-3 rounded-full shadow-lg z-50 border hover:border-green-700 transition-all duration-300 hover:scale-110"
        title="Chatbot Tư Vấn Thuốc"
        onClick={() => setShowChat((prev) => !prev)}
      >
        <SmartToyIcon fontSize="medium" />
      </button>

      {/* Chat window */}
      {showChat && (
        <div
          className="fixed bottom-5 right-20 bg-white rounded-2xl shadow-2xl z-50 border border-green-700 flex flex-col animate-fadeIn"
          style={{ width: "650px", height: "750px" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-green-700 to-green-500 text-white rounded-t-2xl shadow-lg">
            <div className="flex items-center gap-3">
              <span className="bg-white p-2 rounded-full">
                <SmartToyIcon className="text-green-700" fontSize="small" />
              </span>
              <div className="flex flex-col">
                <span className="font-semibold tracking-wide">
                  Chatbot Tư Vấn Thuốc
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={clearChatHistory}
                className="text-white hover:text-green-200 text-sm px-2 py-1 rounded transition-colors hover:bg-green-600"
                title="Xóa lịch sử chat"
              >
                Xóa lịch sử
              </button>
              <button
                onClick={() => setShowChat(false)}
                className="text-white hover:text-green-200 text-2xl leading-none transition-colors hover:scale-110 p-1"
              >
                ×
              </button>
            </div>
          </div>

          {/* Chat body */}
          <div
            className="flex-1 p-4 overflow-y-auto bg-gray-50"
            style={{ minHeight: "500px", maxHeight: "650px" }}
          >
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex mb-4 ${
                  msg.from === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.from === "bot" && (
                  <img
                    src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png"
                    alt="bot"
                    className="w-8 h-8 rounded-full mr-3 border-2 border-green-300 bg-white flex-shrink-0 mt-1"
                  />
                )}
                <div
                  className={`flex flex-col ${
                    msg.from === "user"
                      ? "items-end max-w-sm"
                      : "items-start max-w-xl"
                  }`}
                >
                  <div
                    className={`px-4 py-3 rounded-2xl shadow-md ${
                      msg.from === "user"
                        ? "bg-green-700 text-white rounded-br-none"
                        : msg.isTyping
                        ? "bg-gray-200 text-gray-600 border border-gray-300 rounded-bl-none animate-pulse"
                        : "bg-white text-gray-800 border border-green-100 rounded-bl-none"
                    }`}
                  >
                    {msg.isTyping ? (
                      <div className="text-sm flex items-center gap-2">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                          <div
                            className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                            style={{ animationDelay: "0.1s" }}
                          ></div>
                          <div
                            className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                            style={{ animationDelay: "0.2s" }}
                          ></div>
                        </div>
                        <span>{msg.content}</span>
                      </div>
                    ) : msg.isStructured && typeof msg.content === "object" ? (
                      <StructuredMessage data={msg.content} />
                    ) : (
                      <div className="text-sm whitespace-pre-wrap">
                        {msg.content}
                      </div>
                    )}
                  </div>
                  {msg.timestamp && !msg.isTyping && (
                    <span className="text-xs text-gray-500 mt-1 px-1">
                      {formatTime(msg.timestamp)}
                    </span>
                  )}
                </div>
                {msg.from === "user" && (
                  <img
                    src="https://cdn-icons-png.flaticon.com/512/1946/1946429.png"
                    alt="user"
                    className="w-8 h-8 rounded-full ml-3 border-2 border-gray-300 bg-white flex-shrink-0 mt-1"
                  />
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form
            className="flex border-t border-gray-200 bg-white rounded-b-2xl p-3"
            onSubmit={handleSend}
          >
            <input
              type="text"
              className="flex-1 px-4 py-3 outline-none rounded-lg bg-gray-50 text-gray-800 placeholder-gray-400 border border-gray-200 focus:border-green-500 focus:bg-white transition-all"
              placeholder={
                loading ? "Đang xử lý..." : "Hỏi về thuốc, triệu chứng..."
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              autoFocus
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className={`ml-3 px-6 py-3 font-bold rounded-lg transition-all shadow ${
                loading || !input.trim()
                  ? "bg-gray-400 text-gray-600 cursor-not-allowed"
                  : "bg-green-700 hover:bg-green-800 text-white hover:shadow-lg hover:scale-105"
              }`}
            >
              {loading ? "..." : "Gửi"}
            </button>
          </form>
        </div>
      )}

      {/* Custom CSS */}
      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        .line-clamp-3 {
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </>
  );
};

export default Base;
