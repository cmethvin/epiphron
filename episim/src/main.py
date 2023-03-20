import pubsub.pubsub
import scipy
import numpy as np
import json
from scipy.optimize import minimize
from pert import PERT

PROJECT_ID = "epiphron"
SIM_SUBSCRIPTION_ID = "simulation_topic-sub"
RESULTS_TOPIC_ID = "results_topic"

inflation = [0.015, 0.02, 0.025]  # inputs for inflation assumption -- will only apply to spend annually
# retirePeriod = 30  # input from user on how long they want retirement to be
workYrs = 10  # years of work remaining before income stops

# values below for med risk and high risk are derived from Shiller data: http://www.econ.yale.edu/~shiller/data.htm
lowRisk = [0.005, .01, .015]  # input (P10/50/90) for low risk investments like govt bonds held to maturity or HYSA
midRisk = [-0.08, .025, .13]  # as above but bond index type risk
highRisk = [-0.13, .08, .29]  # high risk like S&P500 index

iterations = 10000  # input from user for how many sims to run? or just fix it?

def minPert(x, y):
    testDist = PERT(x[0], x[1], x[2])
    return (abs(y[0] - PERT.ppf(testDist, 0.1)) + abs(y[1] - PERT.ppf(testDist, 0.5)) + abs(
        y[2] - PERT.ppf(testDist, 0.9)))


def convBeta(x):
    alpha = 1 + (4 * ((x[1] - x[0]) / (x[2] - x[0])))
    beta = 1 + (4 * ((x[2] - x[1]) / (x[2] - x[0])))
    rng = x[2] - x[0]
    low = x[0]
    d = {
        'alpha': alpha,
        'beta': beta,
        'range': rng,
        'min': low
    }
    return d


def run_sim(data):
    retirePeriod = data["retirePeriod"]
    iterCount = 0
    failCount = 0

    finalYrs = []
    finalTotal = []
    results = []
    meanLow = []
    meanMid = []
    meanHigh = []

    lowRiskFinal = minimize(minPert, lowRisk, args=lowRisk, method='nelder-mead', options={'fatol': 0.00000001})
    midRiskFinal = minimize(minPert, midRisk, args=midRisk, method='nelder-mead', options={'fatol': 0.00000001})
    highRiskFinal = minimize(minPert, highRisk, args=highRisk, method='nelder-mead', options={'fatol': 0.00000001})

    lowRiskBeta = convBeta(lowRiskFinal.x)
    midRiskBeta = convBeta(midRiskFinal.x)
    highRiskBeta = convBeta(highRiskFinal.x)

    lowSample = ((scipy.stats.beta.rvs(lowRiskBeta['alpha'], lowRiskBeta['beta'],
                                       size=iterations * (retirePeriod + workYrs), random_state=None) * lowRiskBeta[
                      'range']) + lowRiskBeta['min'])
    midSample = ((scipy.stats.beta.rvs(midRiskBeta['alpha'], midRiskBeta['beta'],
                                       size=iterations * (retirePeriod + workYrs), random_state=None) * midRiskBeta[
                      'range']) + midRiskBeta['min'])
    highSample = ((scipy.stats.beta.rvs(highRiskBeta['alpha'], highRiskBeta['beta'],
                                        size=iterations * (retirePeriod + workYrs), random_state=None) * highRiskBeta[
                       'range']) + highRiskBeta['min'])
    infSample = np.random.normal(inflation[1], (inflation[2] - inflation[1]) / 1.282,
                                 size=iterations * (retirePeriod + workYrs))

    sampleIndex = 0

    dataDump = {
        'lowIntSuc': [0] * (retirePeriod + workYrs),
        'midIntSuc': [0] * (retirePeriod + workYrs),
        'highIntSuc': [0] * (retirePeriod + workYrs),
        'lowIntFail': [0] * (retirePeriod + workYrs),
        'midIntFail': [0] * (retirePeriod + workYrs),
        'highIntFail': [0] * (retirePeriod + workYrs),
        'year': []
    }

    i = 0
    while i < (retirePeriod + workYrs):
        dataDump['year'].append(i + 1)
        i += 1

    while (iterCount < iterations):
        count = 0

        moSpend = 5000  # input from user - this is after tax
        moIncome = 7000  # input from user - after tax
        raiseAboveInf = 0.0  # default assume income matches inflation, this is for additional raises

        postWorkIncome = 1000  # income in retirement -- be that pension or social security

        # need to add after tax income
        # add time remaining on work
        # add raise assumption
        # add time to pay off house and reduce monthly spending

        nullSavings = 20000  # input from user on checking account balance

        lowSavings = 100000  # input from user for low risk investment balance
        midSavings = 500000  # input from user for medium risk investment balance
        highSavings = 800000  # input from user for high risk investment balance

        totalSavings = lowSavings + midSavings + highSavings

        # gets the users savings ratio -- sim will rebalance each year, but could later add option to let this float
        svgRatio = [lowSavings / totalSavings, midSavings / totalSavings, highSavings / totalSavings]

        statsTracker = {
            'lowInt': [0] * (retirePeriod + workYrs),
            'midInt': [0] * (retirePeriod + workYrs),
            'highInt': [0] * (retirePeriod + workYrs),
            'year': [0] * (retirePeriod + workYrs),
            'failure': False
        }

        # while count < retirePeriod*12:
        while count < retirePeriod + workYrs:
            # Sell from accts if not enough for monthly (assume this done once annually)
            # may need to add some transaction fee assumption and test if significant
            # if(count%12) == 0 and (count!=0):

            if count != 0:
                # do annual inflation update to monthly spending
                moSpend = moSpend * (1 + infSample[sampleIndex])
                moIncome = moIncome * (1 + infSample[sampleIndex] + raiseAboveInf)

                # Rebalance accounts annually. Future change may be to allow this ratio to move over time
                tmpRebal = lowSavings + midSavings + highSavings

                lowSavings = tmpRebal * svgRatio[0]
                midSavings = tmpRebal * svgRatio[1]
                highSavings = tmpRebal * svgRatio[2]

            # if nullSavings<moSpend:
            if nullSavings < moSpend * 12:
                # print("selling to get spending money")
                # get the current total savings
                tmpTotal = lowSavings + midSavings + highSavings

                if tmpTotal == 0:
                    curRatio = [0, 0, 0]
                else:
                    curRatio = [lowSavings / tmpTotal, midSavings / tmpTotal, highSavings / tmpTotal]

                # if the total is less than 12 months, consider failure outcome
                if tmpTotal < (moSpend * 12):
                    if (tmpTotal + nullSavings) < moSpend * 12:
                        failCount = failCount + 1
                        # add in logic to store failure averages
                        nullSavings = 0
                        lowSavings = 0
                        midSavings = 0
                        highSavings = 0
                        # print("failing")

                        statsTracker['failure'] = True
                        break
                    else:
                        nullSavings = nullSavings + tmpTotal
                        lowSavings = 0
                        midSavings = 0
                        highSavings = 0

                else:
                    nullSavings = nullSavings + moSpend * 12

                    # remove 1 yr of spending proportionally from each savings bucket
                    lowSavings = (tmpTotal - moSpend * 12) * curRatio[0]
                    midSavings = (tmpTotal - moSpend * 12) * curRatio[1]
                    highSavings = (tmpTotal - moSpend * 12) * curRatio[2]

                    # spend monthly amount for whole year
            if count > workYrs:
                nullSavings = nullSavings - moSpend * 12 + postWorkIncome * 12  # note need a check on inputs that post work income can't be greater than spending
            else:
                if moSpend >= moIncome:
                    nullSavings = nullSavings - moSpend * 12 + moIncome * 12
                else:
                    tmp = (moIncome - moSpend) * 12
                    nullSavings = nullSavings - moSpend * 12
                    lowSavings += tmp

            # apply randomly selected interest to each account
            # tmpLow  = max(0,np.random.normal(lowRisk[1],(lowRisk[2]-lowRisk[1])/1.282,size=1))
            # tmpMid  = max(-1,np.random.normal(midRisk[1],(midRisk[2]-midRisk[1])/1.282,size=1))
            # tmpHigh  = max(-1,np.random.normal(highRisk[1],(highRisk[2]-highRisk[1])/1.282,size=1))

            tmpLow = max(0, lowSample[sampleIndex])
            tmpMid = max(-1, midSample[sampleIndex])
            tmpHigh = max(-1, highSample[sampleIndex])

            statsTracker['lowInt'][count] = tmpLow
            statsTracker['midInt'][count] = tmpMid
            statsTracker['highInt'][count] = tmpHigh
            statsTracker['year'][count] = count

            sampleIndex += 1

            # lowSavings = lowSavings*(1+((1+tmpLow)**(1/12)-1))
            # midSavings = midSavings*(1+((1+tmpMid)**(1/12)-1))
            # highSavings = highSavings*(1+((1+tmpHigh)**(1/12)-1))

            lowSavings *= (1 + tmpLow)
            midSavings *= (1 + tmpMid)
            highSavings *= (1 + tmpHigh)

            count += 1

        tmp = nullSavings + lowSavings + midSavings + highSavings

        finalTotal.append(tmp)
        # finalYrs.append((count-1)/12)
        finalYrs.append(count)

        meanLow.append(np.mean(statsTracker['lowInt']))
        meanMid.append(np.mean(statsTracker['midInt']))
        meanHigh.append(np.mean(statsTracker['highInt']))

        # results = pandas.DataFrame(data=[finalYrs, finalTotal, meanLow, meanMid, meanHigh],columns=['finalYrs', 'finalTotal', 'meanLow', 'meanMid', 'meanHigh'])
        results = {
            'Success Years': finalYrs,
            'Final Savings': finalTotal,
            'Mean Low Int': meanLow,
            'Mean Mid Int': meanMid,
            'Mean High Int': meanHigh
        }

        iterCount += 1

        k = 0
        while k < (retirePeriod + workYrs):
            if statsTracker['failure']:
                dataDump['lowIntFail'][k] = dataDump['lowIntFail'][k] * (failCount - 1) / failCount + \
                                            statsTracker['lowInt'][k] * (1 / failCount)
                dataDump['midIntFail'][k] = dataDump['midIntFail'][k] * (failCount - 1) / failCount + \
                                            statsTracker['midInt'][k] * (1 / failCount)
                dataDump['highIntFail'][k] = dataDump['highIntFail'][k] * (failCount - 1) / failCount + \
                                             statsTracker['highInt'][k] * (1 / failCount)
                k += 1
            else:
                dataDump['lowIntSuc'][k] = dataDump['lowIntSuc'][k] * (iterCount - failCount - 1) / (
                            iterCount - failCount) + statsTracker['lowInt'][k] * (1 / (iterCount - failCount))
                dataDump['midIntSuc'][k] = dataDump['midIntSuc'][k] * (iterCount - failCount - 1) / (
                            iterCount - failCount) + statsTracker['midInt'][k] * (1 / (iterCount - failCount))
                dataDump['highIntSuc'][k] = dataDump['highIntSuc'][k] * (iterCount - failCount - 1) / (
                            iterCount - failCount) + statsTracker['highInt'][k] * (1 / (iterCount - failCount))
                k += 1

    resPercentiles = {
        'Success Years': [],
        'Final Savings': [],
        'Years': [],
        'Mean Low Int': [],
        'Mean Mid Int': [],
        'Mean High Int': [],
        'Percentiles': [],
        'Mean Low Int Fail - Annual': [0] * 101,
        'Mean Mid Int Fail - Annual': [0] * 101,
        'Mean High Int Fail - Annual': [0] * 101,
        'Mean Low Int Success - Annual': [0] * 101,
        'Mean Mid Int Success - Annual': [0] * 101,
        'Mean High Int Success - Annual': [0] * 101,
    }

    i = 0

    while i <= 100:
        resPercentiles['Success Years'].append(np.percentile(results['Success Years'], i))
        resPercentiles['Final Savings'].append(np.percentile(results['Final Savings'], i))
        resPercentiles['Mean Low Int'].append(np.percentile(results['Mean Low Int'], i))
        resPercentiles['Mean Mid Int'].append(np.percentile(results['Mean Mid Int'], i))
        resPercentiles['Mean High Int'].append(np.percentile(results['Mean High Int'], i))
        resPercentiles['Percentiles'].append(i)
        i += 1

    i = 0
    while i < (retirePeriod + workYrs):
        resPercentiles['Mean Low Int Fail - Annual'][i] = dataDump['lowIntFail'][i]
        resPercentiles['Mean Mid Int Fail - Annual'][i] = dataDump['midIntFail'][i]
        resPercentiles['Mean High Int Fail - Annual'][i] = dataDump['highIntFail'][i]
        resPercentiles['Mean Low Int Success - Annual'][i] = dataDump['lowIntSuc'][i]
        resPercentiles['Mean Mid Int Success - Annual'][i] = dataDump['midIntSuc'][i]
        resPercentiles['Mean High Int Success - Annual'][i] = dataDump['highIntSuc'][i]
        resPercentiles['Years'].append(i)
        i += 1

    # print(np.mean(resPercentiles['Mean Low Int']))
    # print(np.mean(dataDump['lowIntFail']))
    # print(np.mean(dataDump['lowIntSuc']))

    #data = pd.DataFrame(data=resPercentiles)
    data = resPercentiles
    print(resPercentiles)

    return data
    

def handle(message, results_publisher):
    data = json.loads(message.data)
    results = run_sim(data)
    response = dict(id=data['id'], results=results)
    results_publisher.publish(PROJECT_ID, RESULTS_TOPIC_ID, response)


if __name__ == "__main__":
    publisher = pubsub.pubsub.ResultsPublisher()

    def callback(message):
        print(f"Received {message}")
        handle(message, publisher)
        message.ack()

    pubsub.pubsub.listen(PROJECT_ID, SIM_SUBSCRIPTION_ID, callback)