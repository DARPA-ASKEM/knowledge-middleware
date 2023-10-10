#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import pandas as pd
from scipy.integrate import odeint
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import scipy.io
from scipy.integrate import solve_ivp
import os
import h5py


# Load data using pandas
data_orig = pd.read_csv('data.csv', parse_dates=['Date'])
#data = scipy.io.loadmat(os.path.join('1-s2.0-S0048969722064257-mmc1','data_SEIRV_fit.mat'))


# In[ ]:


"""
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% This code carries out data fitting for the second wave using the SEIRV
% model. 
%
% NOTE: High titer -> Mean half-life 0.99 days
%       Low titer  -> Mean half-life 7.9 days
%       These values impact tau0 in the getDecay() function.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

rng('default');

clear;clc
set(groot, 'defaultAxesTickLabelInterpreter','latex');
set(groot, 'defaultLegendInterpreter','latex');
set(0,'defaulttextInterpreter','latex','defaultAxesFontSize',16) 
format long

bl = '#0072BD';
br = '#D95319';

%% Load data
load(['data_SEIRV_fit.mat'])

V = cRNA2.*F2;
split = 78; %split 1 week after first day of vaccine (12/11/2020)
V = V(1:split);
tspan = 1:length(V);

%% Curve-fitting
options = optimoptions('fmincon','TolX',1e-12,'TolFun',1e-12,'MaxIter',50000,'MaxFunEvals',100000,'display','off');

  beta_fixed = 4.48526e7;
    lb = [0     51    beta_fixed  10 ];
    ub = [1E-4  796   beta_fixed  5000];
    p0 = [9.06e-08 360 beta_fixed 1182];

% 
%% try Global Search
gs = GlobalSearch;
ms = MultiStart('Display','iter');

problem = createOptimProblem('fmincon','x0',p0,...
    'objective',@(param)obj_fun(param,tspan,V),'lb',lb,'ub',ub);

[best_params,SSE] = run(ms,problem,25);

parameter = ["lambda";"alpha";"beta";"E(0)";"SSE"];
estimated_val = [best_params';SSE];
t = table(parameter,estimated_val)

%% Simulate with best params

alpha = best_params(2);
beta = best_params(3);

traveltime = 18; % hours
k = getDecay(1); % use first time point

eta = 1 - exp(-k*traveltime);

% total population served by DITP
N0 = 2300000;

E0 = best_params(4);
I0 = V(1)/(alpha*beta*(1-eta));
R0 = 0;
S0 = N0 - (E0 + I0 + R0);
V0 = V(1); % use first data point 
ICs  = [S0 E0 I0 R0 V0 E0];

[T,Y] = ode45(@SEIRV,1:length(cRNA2),ICs,[],best_params);


%% Plot
time = datetime(2020,9,30) + caldays(0:length(cRNA2)-1);

figure()
    t = tiledlayout(1,2);

    nexttile
    plot(time2(2:end),log10(diff(Y(:,5))),'LineWidth',2); hold on
    plot(time2(2:end),log10(cRNA2(2:end).*F2(2:end)),'.','markersize',20,'LineWidth',2,'Color',br);
    ylabel('$\log_{10}$ viral RNA copies')
    xline(split,'--','LineWidth',2,'Color',[0 1 0])
    ylim([13.5 inf])
    xlim([time(18-1) time(116-1)])


    nexttile
    plot(time(2:end),log10(diff(Y(:,6))),'LineWidth',2); hold on
    p2 = plot(time2(2:end),log10(newRepCases2(2:end)),'LineWidth',2,'Color',br);
    ylabel('$\log_{10}$ Daily Incidence');

    [max1,index1] = max(diff(Y(:,6))); %simulation max
    xline(time2(index1+1),'--','LineWidth',2,'Color',bl)
    [max2,index2] = max(newRepCases2); %simulation max
    xline(time2(index2),'--','LineWidth',2,'Color',br)

    legend('Model','Data','Location','NorthWest')
    ylim([2.379 4.5])
    xlim([time2(2) time2(118)])

    hold off
    
    %%
    
    f = gcf;
    exportgraphics(f,'fitting_with_temperature.pdf','Resolution',600)

    %%
    
    figure
    box on; hold on;

    %estimate R
    y = (diff(Y(:,6)));
    x = (newRepCases2(2:end));
    X = [ones(length(x),1) x];
    b = X\y;

    yCalc2 = X*b;%b1*x;
    scatter(x,y,20,'k','LineWidth',2);
    plot(x,yCalc2,'r','LineWidth',2)
    ylim([0 inf])

    ylabel('Predicted cases');
    xlabel('Reported cases')

    %calculate R2
    Rsq2 = 1 - sum((y-yCalc2).^2)/sum((y-mean(y)).^2);

    R = corrcoef(x,y); 

    f = gcf;
    exportgraphics(f,'corr_1.pdf','Resolution',600)
%% functions

function err = obj_fun(param,tspan,data)
    traveltime = 18;% hours
    k = getDecay(1); % use first time point

    eta = 1 - exp(-k*traveltime);

    % total population served by DITP
    N0 = 2300000;

    E0 = param(4);
    I0 = data(1)/(param(2)*param(3)*(1-eta));
    R0 = 0;
    S0 = N0 - (E0 + I0 + R0);
    V0 = data(1);                
    ICs  = [S0 E0 I0 R0 V0 E0];

    [~,Y] = ode45(@SEIRV,tspan,ICs,[],param(1:4));

    % get daily virus
    cumVirus = Y(:,5);
    dailyVirus = diff(cumVirus);

    temp = log10(data(2:end)) - log10(abs(dailyVirus));
    adiff = rmmissing(temp);

    err = sum((adiff).^2);
end

function k = getDecay(t)
    % compute temperature-adjusted decay rate of viral RNA
    
    % high titer -> tau0 = 0.99 days * 24 hours/day = 23.76
    % low titer  -> tau0 = 7.9 days * 24 hours/day  = 189.6

    tau0 = 189.6;%23.76;
    Q0 = 2.5;
    T0 = 20;

    % get current temperature using best-fit sine function
    A = 3.624836409841919;
    B = 0.020222716119084;
    C = 4.466530666828714;
    D = 16.229757918464635;

    T = A*np.sin(B*t - C) + D;

    tau = tau0*Q0**(-(T - T0)/10);

    k = np.log(2)/tau;

end




function dy = SEIRV(t,y,param)
    % parameters to be fit
    lambda = param(1);
    alpha = param(2);
    beta = param(3);

    dy = zeros(6,1);
    
    S = y(1);  
    E = y(2);      
    I = y(3);
    R = y(4);
    V = y(5);

    traveltime = 18; % hours
    k = getDecay(t);

    eta = 1 - exp(-k*traveltime);

    sigma = 1/3;
    gamma = 1/8;
    

    dy(1) = -lambda*S*I;
    dy(2) = lambda*S*I - sigma*E;                               
    dy(3) = sigma*E - gamma*I;
    dy(4) = gamma*I;
    dy(5) = alpha*beta*(1-eta)*I;
    dy(6) = lambda*S*I;       % track cumulative cases
end
"""


# In[ ]:


#remake all the functions
def SEIRV(y, t, lambd, alpha, beta):
    #parameters to be fit
    #eta = param[0] #was lambda but that's a special word in python
    #alpha = param[1]
    #beta = param[2]
    #eta, alpha, beta, E0=param
    dy = np.zeros(6)
    #print(f'y: {y}')
    S, E, I, R, V, cases = y
    #S = y[0]
    #E = y[1]
    #I = y[2]
    #R = y[3]
    #V = y[4]
    traveltime = 18#hours
    k = getDecay(t)#

    eta = 1 - np.exp(-k*traveltime)

    sigma = 1/3
    gamma = 1/8
    

    dy[0] = -lambd*S*I
    dy[1] = lambd*S*I - sigma*E                          
    dy[2] = sigma*E - gamma*I
    dy[3] = gamma*I
    dy[4] = alpha*beta*(1-eta)*I
    dy[5] = lambd*S*I       #track cumulative cases
    return(dy)


def getDecay(t):
    # compute temperature-adjusted decay rate of viral RNA
    
    # high titer -> tau0 = 0.99 days * 24 hours/day = 23.76
    # low titer  -> tau0 = 7.9 days * 24 hours/day  = 189.6

    tau0 = 189.6 #23.76;
    Q0 = 2.5
    T0 = 20

    #get current temperature using best-fit sine function
    A = 3.624836409841919
    B = 0.020222716119084
    C = 4.466530666828714
    D = 16.229757918464635

    T = A*np.sin(B*t - C) + D

    tau = tau0*Q0**(-(T - T0)/10)

    k = np.log(2)/tau
    return(k)

def obj_fun(param,tspan,data):
    #lambd = param[0] #was lambda but that's a special word in python
    #alpha = param[1]
    #beta = param[2]
    lambd, alpha, beta, E0 = param
    traveltime = 18 #hours
    k = getDecay(1)#use first time point

    eta = 1 - np.exp(-k*traveltime)

    #total population served by DITP
    N0 = 2300000

    #E0 = param[3]
    I0 = data[0]/(param[1]*param[2]*(1-eta))
    R0 = 0
    S0 = N0 - (E0 + I0 + R0)
    V0 = data[0]
    cases0=0
    ICs  = [S0,E0,I0,R0,V[0], cases0]
    #print(f'ICs: {ICs}')
    #print(f'tspan: {tspan}')
    #print(f'param: {param}')
    results = odeint(SEIRV, ICs, tspan, args=(lambd, alpha, beta))
    #err = np.sum(np.log10(results[:, 4]) - np.log10(data**2))
    cumVirus=results[:, 5]
    dailyVirus = np.diff(cumVirus)
    temp = np.log10(data[1:])-np.log10(np.abs(dailyVirus))
    adiff = temp[~np.isnan(temp)] #remove NAs
    err = np.sum(adiff**2)
    """
    cumVirus = Y(:,5); I got rid of dy[5] becaues it was causing issues
    #get daily virus
    dailyVirus = diff(cumVirus)

    temp = log10(data(2:end)) - log10(abs(dailyVirus))
    adiff = rmmissing(temp)

    err = sum((adiff).^2)
    """
    return(err)


# In[ ]:


data = data_orig.tail(225).reset_index()
data['V'] = data['cRNA2']*data['F2']
split = 78; #plit 1 week after first day of vaccine (12/11/2020)
V=data.iloc[:split]['V']
data['tspan'] = (data['Date'] - data['Date'].min()).dt.days
tspan=data.iloc[:split]['tspan']

#Curve-fitting
beta_fixed = 4.48526*10**7
lb = [0,51,beta_fixed,10]
ub = [0.0001,796,beta_fixed,5000]
p0 = [9.06*10**(-8),360,beta_fixed,1182]


# Perform parameter estimation
#result = minimize(obj_fun, p0, args=(eta, alpha, beta, E0), bounds=list(zip(lb, ub)))
result = minimize(obj_fun, p0, args=(tspan, V), bounds=list(zip(lb, ub)))
params_opt = result.x
alpha = params_opt[1]
beta = params_opt[2]
traveltime = 18#hours
k = getDecay(1)#use first time point
eta = 1 - np.exp(-k*traveltime)
#total population served by DITP
N0 = 2300000
E0 = params_opt[3]
I0 = V[0]/(alpha*beta*(1-eta))
R0 = 0
S0 = N0 - (E0 + I0 + R0)
V0 = V[0] # use first data point 
cases0=0
ICs  = [S0,E0,I0,R0,V0,cases0]
#def SEIRV(y, t, eta, alpha, beta):

sol_opt = odeint(SEIRV, ICs, tspan, args=tuple(params_opt[:3]))

#solve it further in time?
tspan2=data['tspan']
sol_opt2 = odeint(SEIRV, ICs, tspan2, args=tuple(params_opt[:3]))

# Plotting
plt.figure()
plt.plot(tspan, np.log10(V), 'bo', label='Train')
plt.plot(tspan[1:], np.log10(np.diff(sol_opt[:, 4])), 'k-', label='Train Fitting')
plt.plot(tspan2[split+1:], np.log10(np.diff(sol_opt2[split:, 4])), 'g-', label='Train Fitting')
plt.scatter(data['tspan'][split:], np.log10(data['V'][split:]), color='red', label='Test Fitting')
plt.xlabel('Time')
plt.ylabel('Viral RNA in wastewater')
plt.legend()
plt.show()


# Best fit parameters: λ = 9.66 × 10−8 day−1person−1, α = 249 g, γ = 0.08, and E(0) = 11 people) as well as the fixed beta (4.49*10^7)

# In[ ]:


#lambd, alpha, beta, E0 = param
params_best=[9.66*10**(-8), 240, 4.49*10**7, 11]
sol_opt = odeint(SEIRV, ICs, tspan, args=tuple(params_best[:3]))

#solve it further in time?
tspan2=data['tspan']
sol_opt2 = odeint(SEIRV, ICs, tspan2, args=tuple(params_best[:3]))

# Plotting
plt.figure()
plt.plot(tspan, np.log10(V), 'bo', label='Train')
plt.plot(tspan[1:], np.log10(np.diff(sol_opt[:, 4])), 'k-', label='Train Fitting')
plt.plot(tspan2[split+1:], np.log10(np.diff(sol_opt2[split:, 4])), 'g-', label='Train Fitting')
plt.scatter(data['tspan'][split:], np.log10(data['V'][split:]), color='red', label='Test Fitting')
plt.xlabel('Time')
plt.ylabel('Viral RNA in wastewater')
plt.legend()
plt.show()

