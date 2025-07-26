#!/usr/bin/env python3
"""
Banner utility for SEOFrog
Displays application banner and version information
"""

def print_banner():
    """Print SEOFrog application banner"""
    banner_text = """
==================================================================
                                                                  
   #######  #######  #######  #######  #######   #######  ######
   #        #        #     #  #        #     #  #       # #     
   #######  ######   #     #  ######   #######  #       # #   ##
         #  #        #     #  #        #   #    #       # #    #
   #######  #######  #######  #        #    #    #######   ######
                                                                  
                    SEO Analysis & Crawling Tool                 
                           Version 0.2                          
                         Enterprise Edition                      
                                                                 
    -> Comprehensive SEO Analysis & Website Crawling           
    -> Technical SEO Issues Detection                          
    -> Performance & Content Analysis                          
    -> Anti-Loss Recovery System                               
                                                                 
==================================================================

=> Starting SEOFrog Enterprise v0.2...
"""
    
    try:
        print(banner_text)
    except UnicodeEncodeError:
        # Fallback ASCII banner for Windows console
        ascii_banner = """
==================================================================
                                                                  
   #######  #######  #######  #######  #######   #######  ######
   #        #        #     #  #        #     #  #       # #     
   #######  ######   #     #  ######   #######  #       # #   ##
         #  #        #     #  #        #   #    #       # #    #
   #######  #######  #######  #        #    #    #######   ######
                                                                  
                    SEO Analysis & Crawling Tool                 
                           Version 0.2                          
                         Enterprise Edition                      
                                                                 
    -> Comprehensive SEO Analysis & Website Crawling           
    -> Technical SEO Issues Detection                          
    -> Performance & Content Analysis                          
    -> Anti-Loss Recovery System                               
                                                                 
==================================================================

=> Starting SEOFrog Enterprise v0.2...
"""
        print(ascii_banner)