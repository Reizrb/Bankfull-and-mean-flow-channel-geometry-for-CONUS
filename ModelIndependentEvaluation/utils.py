#!/usr/bin/env python
# coding: utf-8

# In[ ]:

import pandas as pd
import numbers
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(style='darkgrid')


plt.rcParams.update({
    # 'font.sans-serif': 'Comic Sans MS',
    #'font.family': 'serif'
})


def calculate_average(fid_array, dataframe):
    subset_df = dataframe[dataframe['COMID'].isin(fid_array)]
    average_ = subset_df.mean(numeric_only=True)
    return average_

def Performance_metrics(X, Y, YesorNo):
    X = np.array(X).reshape(-1,)
    Y = np.array(Y).reshape(-1,)
    r2 = np.corrcoef(X, Y)[0, 1]**2
    abs_pbias = 100 * np.sum(abs(Y - X)) / np.sum(X)
    nse = 1 - np.sum((X - Y)**2) / np.sum((X - np.mean(X))**2)
    rmse = np.sqrt(np.mean(np.square(X - Y)))
    r = np.corrcoef(X, Y)[0, 1]
    s = np.std(Y) / np.std(X)
    b = np.mean(Y) / np.mean(X)
    kge = 1 - np.sqrt((r - 1)**2 + (s - 1)**2 + (b - 1)**2)
    if YesorNo == "Yes":
        return format(r2, ".2f"), format(nse, ".2f"), format(kge, ".2f"), format(abs_pbias, ".2f"), format(rmse, ".2f")
    elif YesorNo == "No":
        print(f'R\N{SUPERSCRIPT TWO}: {r2:.3f}, NSE: {nse:.3f}, KGE: {kge:.3f}, abs_PBias%: {abs_pbias:.3f}, RMSE: {rmse:.3f}')
        
def Scatter_Violin_Plots(X, Y, x, y, Xlable1, Ylable1, Ylable2, Modelname1, Modelname2, title, text1, text2):
    fc = ['#264653', '#5DA5A5']
    X = np.array(X).reshape(-1,)
    Y = np.array(Y).reshape(-1,)
    max_value_X = np.array((X, Y)).max()
    min_value_X = np.array((X, Y)).min()
    max_value_x = np.array((x, y)).max()
    min_value_x = np.array((x, y)).min()
    
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(ncols=4, figsize=(24, 7), constrained_layout= True)
    
    
    ax1.scatter(X, Y, color=fc[0], edgecolor='k',  alpha=0.7, s=100) 
    ax1.set_yscale('log')
    ax1.set_xscale('log')
    ax1.plot([0, 1.8*max_value_X], [0, 1.8*max_value_X], '--', color='#C34A24', linewidth=4)
    ax1.set_xlabel(f'{Xlable1}', fontsize=26)
    ax1.set_ylabel(f'{Ylable1}', fontsize=26)
    ax1.grid(True)
    ax1.set_xlim(0.5*min_value_X, 1.8*max_value_X)
    ax1.set_ylim(0.5*min_value_X, 1.8*max_value_X)
    ax1.set_facecolor("#F0F0F0")   
    ax1.set_title(f'{Modelname1}', size=30)
    ax1.tick_params(labelsize=24)
    
    ax2.scatter(x, y, color=fc[1], edgecolor='k',  alpha=0.7, s=100) 
    ax2.set_yscale('log')
    ax2.set_xscale('log')
    ax2.plot([0, 1.8*max_value_x], [0, 1.8*max_value_x], '--', color='#C34A24', linewidth=4)
    ax2.set_xlabel(f'{Xlable1}', fontsize=26)
    ax2.set_ylabel(f'{Ylable1}', fontsize=26)
    ax2.grid(True)
    ax2.set_xlim(0.5*min_value_x, 1.8*max_value_x)
    ax2.set_ylim(0.5*min_value_x, 1.8*max_value_x)
    ax2.set_facecolor("#F0F0F0")   
    ax2.set_title(f'{Modelname2}', size=30)
    ax2.tick_params(labelsize=24)
    
    data = pd.DataFrame({'Observed':X, 'Predicted':Y})
    data = data.melt()
    data.rename(columns = {'value':'counts'}, inplace = True)
    data[' '] = ' '
    sns.violinplot(data=data, y='counts', split=True, hue='variable',  x=' ', color=fc[0], ax=ax3, linewidth=2.5, width=0.9)
    ax3.set_facecolor("#F0F0F0")  
    ax3.grid(True)
    ax3.set_ylabel(f'{Ylable2}', fontsize=26)
    ax3.set_title(f'{Modelname1}', size=30)
    ax3.tick_params(labelsize=24)
    ax3.legend(title=False, facecolor = "w", fontsize=26, loc='lower center', bbox_to_anchor=(0.5, -0.23), ncol=2 , columnspacing=0.8, handletextpad=0.3, handlelength=0.8)
    
    data = pd.DataFrame({'Observed':x, 'Predicted':y})
    data = data.melt()
    data.rename(columns = {'value':'counts'}, inplace = True)
    data[' '] = ' '
    sns.violinplot(data=data, y='counts', split=True, hue='variable',  x=' ', color=fc[1], ax=ax4, linewidth=2.5, width=0.9)
    ax4.set_facecolor("#F0F0F0")  
    ax4.grid(True)
    ax4.set_ylabel(f'{Ylable2}', fontsize=26)
    ax4.set_title(f'{Modelname2}', size=30)
    ax4.tick_params(labelsize=24)
    ax4.legend(title=False, facecolor = "w", fontsize=26, loc='lower center', bbox_to_anchor=(0.5, -0.23), ncol=2 , columnspacing=0.8, handletextpad=0.3, handlelength=0.8)   
    fig.text(0.05, 0.74, f'{text1}', size= 22)   
    fig.text(0.3, 0.74, f'{text2}', size= 22)  
    fig.suptitle(f'{title}', size=36, x= 0.5)
    plt.show()        

def Merge_Multiple_Files(dfs, on_what):
    Indep_var_reache = dfs[0]
    for df in dfs[1:len(dfs)]: 
        Indep_var_reache = pd.merge(Indep_var_reache, df, how="left", on=on_what)
    return Indep_var_reache