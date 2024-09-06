CREATE TABLE IF NOT EXISTS "cpu" (                                                                                                   
  "hostname" STRING NULL,                                                                                                            
  "region" STRING NULL,                                                                                                              
  "datacenter" STRING NULL,                                                                                                          
  "rack" STRING NULL,                                                                                                                
  "os" STRING NULL,                                                                                                                  
  "arch" STRING NULL,                                                                                                                
  "team" STRING NULL,                                                                                                                
  "service" STRING NULL,                                                                                                             
  "service_version" STRING NULL,                                                                                                     
  "service_environment" STRING NULL,                                                                                                 
  "usage_user" BIGINT NULL,                                                                                                          
  "usage_system" BIGINT NULL,                                                                                                        
  "usage_idle" BIGINT NULL,                                                                                                          
  "usage_nice" BIGINT NULL,                                                                                                          
  "usage_iowait" BIGINT NULL,                                                                                                        
  "usage_irq" BIGINT NULL,                                                                                                           
  "usage_softirq" BIGINT NULL,                                                                                                       
  "usage_steal" BIGINT NULL,                                                                                                         
  "usage_guest" BIGINT NULL,                                                                                                         
  "usage_guest_nice" BIGINT NULL,                                                                                                    
  "ts" TIMESTAMP(9) NOT NULL,                                                                                                        
  TIME INDEX ("ts")
)                                                                                                                                    
                                                                                                                                     
ENGINE=mito                                                                                                                          
with('append_mode'='true');
