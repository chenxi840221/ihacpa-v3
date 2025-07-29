#!/usr/bin/env python3
"""
Simple Azure OpenAI Test for IHACPA v2.0
Tests just the Azure OpenAI connection without Redis or complex imports
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_azure_openai_direct():
    """Test Azure OpenAI connection directly"""
    print("🔷 Simple Azure OpenAI Connection Test")
    print("=" * 45)
    
    # Check environment
    azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    azure_key = os.getenv('AZURE_OPENAI_KEY')
    azure_model = os.getenv('AZURE_OPENAI_MODEL')
    azure_version = os.getenv('AZURE_OPENAI_API_VERSION')
    
    print(f"📋 Configuration:")
    print(f"   Endpoint: {azure_endpoint}")
    print(f"   Model: {azure_model}")
    print(f"   API Version: {azure_version}")
    print(f"   API Key: {'✅ Set' if azure_key else '❌ Missing'}")
    
    if not all([azure_endpoint, azure_key, azure_model, azure_version]):
        print("❌ Missing required Azure OpenAI configuration")
        return False
    
    # Test connection with OpenAI library
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=azure_key,
            api_version=azure_version
        )
        
        print("\n🤖 Testing Azure OpenAI connection...")
        
        # Simple test completion
        response = client.chat.completions.create(
            model=azure_model,
            messages=[{
                "role": "user",
                "content": "Respond with exactly: 'Azure OpenAI connection successful'"
            }],
            max_tokens=20,
            temperature=0
        )
        
        result = response.choices[0].message.content
        print(f"   Response: {result}")
        
        if "successful" in result.lower():
            print("✅ Azure OpenAI connection test PASSED!")
            return True
        else:
            print("❌ Unexpected response from Azure OpenAI")
            return False
            
    except Exception as e:
        print(f"❌ Azure OpenAI connection failed: {e}")
        return False

async def test_langchain_azure():
    """Test LangChain with Azure OpenAI"""
    print("\n🔗 Testing LangChain + Azure OpenAI")
    print("=" * 35)
    
    try:
        from langchain_openai import AzureChatOpenAI
        
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key=os.getenv('AZURE_OPENAI_KEY'),
            azure_deployment=os.getenv('AZURE_OPENAI_MODEL'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            temperature=0
        )
        
        result = await llm.ainvoke("Say 'LangChain Azure test successful'")
        print(f"   LangChain Response: {result.content}")
        
        if "successful" in result.content.lower():
            print("✅ LangChain + Azure OpenAI test PASSED!")
            return True
        else:
            print("❌ Unexpected LangChain response")
            return False
            
    except Exception as e:
        print(f"❌ LangChain test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🔷 IHACPA v2.0 - Azure OpenAI Integration Verification")
    print("=" * 60)
    
    # Test direct connection
    direct_test = await test_azure_openai_direct()
    
    # Test LangChain integration
    langchain_test = await test_langchain_azure()
    
    print(f"\n🎯 Test Results:")
    print(f"   Direct Azure OpenAI: {'✅ PASS' if direct_test else '❌ FAIL'}")
    print(f"   LangChain Integration: {'✅ PASS' if langchain_test else '❌ FAIL'}")
    
    if direct_test and langchain_test:
        print("\n🎉 All Azure OpenAI tests PASSED!")
        print("✅ IHACPA v2.0 Azure integration is working correctly")
        print()
        print("📋 Next Steps:")
        print("   1. Set up Redis for caching (optional)")
        print("   2. Fix import paths for full demo")
        print("   3. Test with real vulnerability data")
        print("   4. Begin migration from v1.0")
        return True
    else:
        print("\n❌ Some tests failed - check configuration")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())