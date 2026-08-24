package example;

public final class OrderChangeService {
    public boolean requiresPlanningReview(boolean scheduled) {
        return scheduled;
    }
}
